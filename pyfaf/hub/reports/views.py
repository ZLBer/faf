import os
import uuid
import json
import pyfaf
import datetime

from django.http import HttpResponse
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.views.decorators.csrf import csrf_exempt

from sqlalchemy import func
from sqlalchemy.sql.expression import desc, literal, distinct

from pyfaf import ureport
from pyfaf.storage.opsys import OpSys, OpSysComponent, Package
from pyfaf.storage.report import Report, ReportOpSysRelease, ReportHistoryDaily, ReportHistoryWeekly, ReportHistoryMonthly, ReportPackage, ReportRelatedPackage
from pyfaf.hub.reports.forms import NewReportForm, ReportFilterForm, ReportOverviewForm

def date_iterator(first_date, time_unit='d', end_date=None):
    if time_unit == 'd':
        next_date_fn = lambda x : x + datetime.timedelta(days=1)
    elif time_unit == 'w':
        first_date -= datetime.timedelta(days=first_date.weekday())
        next_date_fn = lambda x : x + datetime.timedelta(weeks=1)
    elif time_unit == 'm':
        first_date = first_date.replace(day=1)
        next_date_fn = lambda x : (x.replace(day=25) + datetime.timedelta(days=7)).replace(day=1)
    else:
        raise ValueError('Unknown time unit type : "%s"' % time_unit)

    toreturn = first_date
    yield toreturn
    while True:
        toreturn = next_date_fn(toreturn)
        if not end_date is None and toreturn>end_date:
            break

        yield toreturn

def chart_data_generator(chart_data, dates):
    last_value = 0
    reports = iter(chart_data)
    report = next(reports)

    for date in dates:
        if date < report[0]:
            yield (date,last_value)
        else:
            last_value = report[1]
            yield report
            report = next(reports)

def release_accumulated_history(db, osrelease_ids, component_ids, duration_opt):
    if duration_opt == 'd':
        hist_column = ReportHistoryDaily.day
        hist_table = ReportHistoryDaily
    elif duration_opt == 'w':
        hist_column = ReportHistoryWeekly.week
        hist_table = ReportHistoryWeekly
    elif duration_opt == 'm':
        hist_column = ReportHistoryMonthly.month
        hist_table = ReportHistoryMonthly
    else:
        raise ValueError('Unknown duration option : "%s"' % duration_opt)

    counts_per_date = db.session.query(hist_column.label('time'),func.sum(hist_table.count).label('count'))\
            .group_by(hist_column)

    if osrelease_ids:
        counts_per_date = counts_per_date.filter(hist_table.opsysrelease_id.in_(osrelease_ids))

    if component_ids:
        counts_per_date = counts_per_date.outerjoin(Report, Report.id==ReportOpSysRelease.report_id)\
                .filter(Report.component_id.in_(component_ids))

    counts_per_date = counts_per_date.subquery()

    hist_dates = db.session.query(distinct(hist_column).label('time'))\
            .subquery()

    accumulated_date_counts = db.session.query(hist_dates.c.time, func.sum(counts_per_date.c.count))\
                    .filter(hist_dates.c.time>=counts_per_date.c.time)\
                    .group_by(hist_dates.c.time)\
                    .order_by(hist_dates.c.time)\
                    .all();

    hist_mindate = db.session.query(func.min(hist_column).label('value')).one()
    hist_mindate = hist_mindate[0] if not hist_mindate[0] is None  else datetime.date.today()

    displayed_dates = (d for d in date_iterator(hist_mindate, duration_opt, datetime.date.today()))

    if accumulated_date_counts:
        chart_data = (report for report in chart_data_generator(accumulated_date_counts, displayed_dates))
    else:
        chart_data = ((date,0) for date in displayed_dates)

    return chart_data


def index(request, *args, **kwargs):
    db = pyfaf.storage.getDatabase()
    params = dict(request.REQUEST)
    params.update(kwargs)
    form = ReportOverviewForm(db, params)

    duration_opt = form.get_duration_selection()
    component_ids = form.get_component_selection()

    reports = ((name, release_accumulated_history(db, ids, component_ids,
    duration_opt)) for ids, name in form.get_release_selection())

    forward = {'reports' : reports, 'duration' : duration_opt, 'form' : form}

    return render_to_response('reports/index.html', forward, context_instance=RequestContext(request))

def listing(request, *args, **kwargs):
    db = pyfaf.storage.getDatabase()
    params = dict(request.REQUEST)
    params.update(kwargs)
    form = ReportFilterForm(db, params)

    statuses = db.session.query(Report.id, literal('NEW').label('status')).filter(Report.problem_id==None).subquery()

    if form.get_status_selection() == 'fixed':
        statuses = db.session.query(Report.id, literal('FIXED').label('status')).filter(Report.problem_id!=None).subquery()

    opsysrelease_id = form.os_release_id
    reports = db.session.query(Report.id, literal(0).label('rank'), statuses.c.status, Report.first_occurence.label('created'), Report.last_occurence.label('last_change'), OpSysComponent.name.label('component'))\
        .join(ReportOpSysRelease)\
        .join(OpSysComponent)\
        .filter(statuses.c.id==Report.id)\
        .filter((ReportOpSysRelease.opsysrelease_id==opsysrelease_id) | (opsysrelease_id==-1))\
        .order_by(desc('last_change'))

    component_ids = form.get_component_selection()
    if component_ids:
        reports = reports.filter(Report.component_id.in_(component_ids))

    reports = reports.all()

    i = 1
    for r in reports:
        r.rank = i
        i+=1

    forward = {'reports' : reports,
               'form'  : form}

    return render_to_response('reports/list.html', forward, context_instance=RequestContext(request))

def item(request, report_id):
    db = pyfaf.storage.getDatabase()
    report = db.session.query(Report, OpSysComponent, OpSys).join(OpSysComponent).join(OpSys).filter(Report.id==report_id).first()
    history_select = lambda table : db.session.query(table).filter(table.report_id==report_id).all()
    daily_history = history_select(ReportHistoryDaily)
    weekly_history = history_select(ReportHistoryWeekly)
    monthly_history = history_select(ReportHistoryMonthly)

    packages = db.session.query(Package.name)\
                                                        .filter(Package.id==ReportPackage.installed_package_id)\
                                                        .filter(ReportPackage.report_id==report_id)\
                     .union_all(db.session.query(Package.name)\
                                                        .filter(Package.id==ReportRelatedPackage.installed_package_id)\
                                                        .filter(ReportRelatedPackage.report_id==report_id))\
                     .all()


    return render_to_response('reports/item.html',
                                {'report':report,
                                 'daily_history':daily_history,
                                 'weekly_history':weekly_history,
                                 'monthly_history':monthly_history,
                                 'packages':packages},
                                context_instance=RequestContext(request))

@csrf_exempt
def new(request):
    if request.method == 'POST':
        form = NewReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.cleaned_data['file']['converted']
            try:
                known = ureport.is_known(report, pyfaf.storage.Database())
            except:
                known = False

            spool_dir = pyfaf.config.get('Report.SpoolDirectory')
            fname = str(uuid.uuid4())
            with open(os.path.join(spool_dir, 'incoming', fname), 'w') as f:
                f.write(form.cleaned_data['file']['json'])

            if 'application/json' in request.META.get('HTTP_ACCEPT'):
                response = {'known': known}
                return HttpResponse(json.dumps(response),
                    mimetype='application/json')

            return render_to_response('reports/success.html',
                {'report': report, 'known': known},
                context_instance=RequestContext(request))
        else:
            if 'application/json' in request.META.get('HTTP_ACCEPT'):
                return HttpResponse(status=400, mimetype='application/json')

            return render_to_response('reports/new.html', {'form': form},
                context_instance=RequestContext(request))
    else:
        form = NewReportForm()

    return render_to_response('reports/new.html', {'form': form},
        context_instance=RequestContext(request))

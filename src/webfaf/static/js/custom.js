$(document).ready(function() {
    $.each($('.multiselect'), function(index, value) {
      $(this).multiselect({
        includeSelectAllOption: true,
        selectAllValue: 'select-all',
        nonSelectedText: $("label[for='"+$(this).attr("id")+"']").text(),
      });
    });

    $.each($('.multiselect-filtered'), function(index, value) {
      $(this).multiselect({
        includeSelectAllOption: true,
        selectAllValue: 'select-all',
        enableFiltering: true,
        maxHeight: 200,
        nonSelectedText: $("label[for='"+$(this).attr("id")+"']").text(),
      });
    });
    $.each($('.multiselect-filtered-dynamic'), function(index, value) {
      var $this = $(this);
      var optionsHtml = $this.html();
      $this.find("option:not(:selected)").remove();
      $this.multiselect({
        includeSelectAllOption: true,
        selectAllValue: 'select-all',
        enableFiltering: true,
        maxHeight: 200,
        nonSelectedText: $("label[for='"+$this.attr("id")+"']").text(),
        onDropdownShow: function(event) {
          $this.multiselect('destroy');
          $this.html(optionsHtml);
          $this.multiselect({
            includeSelectAllOption: true,
            selectAllValue: 'select-all',
            enableFiltering: true,
            enableCaseInsensitiveFiltering: true,
            maxHeight: 200,
            nonSelectedText: $("label[for='"+$this.attr("id")+"']").text(),
          });
          $this.parent().find(".btn.multiselect").click();
        }
      });
    });

    var component_names = new Bloodhound({
      datumTokenizer: Bloodhound.tokenizers.obj.whitespace('name'),
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      prefetch: {
        url: ROOT_URL+'component_names.json',
        filter: function(list) {
          return $.map(list, function(componentName) {
            return { name: componentName }; });
        }
      }
    });
    component_names.initialize();
    $('input.component-names').tagsinput({
      typeaheadjs: {
        name: 'component_names',
        displayKey: 'name',
        valueKey: 'name',
        source: component_names.ttAdapter()
      }
    });

    $('input.daterange').daterangepicker({
      locale: {
        // Set Monday as the first day of the week.
        firstDay: 1
      },
      ranges: {
        //'Today': [moment(), moment()],
        'Yesterday': [moment().subtract(1, 'days'), moment().subtract(1, 'days')],
        'Last 7 Days': [moment().subtract(6, 'days'), moment()],
        'Last 14 Days': [moment().subtract(13, 'days'), moment()],
        'Last 30 Days': [moment().subtract(29, 'days'), moment()],
        'This Month': [moment().startOf('month'), moment().endOf('month')],
        'Last Month': [moment().subtract(1, 'month').startOf('month'), moment().subtract(1, 'month').endOf('month')]
      },
      startDate: moment().subtract(13, 'days'),
      endDate: moment(),
      format: 'YYYY-MM-DD',
      separator: ':',
    });

    $('.btn-more').click(function() {
      $(this).parents('table').find('tr.package.hide').removeClass('hide');
      $(this).parents('tr').remove();
      return false;
    });

    $('.btn-toggle-versions').click(function() {
      const $parentTable = $(this).parents('table').first();

      if ($parentTable.data('versionsShown')) {
        $parentTable.find('tr.version').addClass('hide');
        $parentTable.find('tr.package').removeClass('stripe');
        $(this).text('Show versions');
        $parentTable.data('versionsShown', 0);
      } else {
        $parentTable.find('.btn-more').click();
        $parentTable.find('tr.version').removeClass('hide');
        $parentTable.find('tr.package').addClass('stripe');
        $(this).text('Hide versions');
        $parentTable.data('versionsShown', 1);
      }
    });

    function sort_table($table, col) {
      var order = 'asc'
      if($table.data('sortCol') == col) {
        if($table.data('sortOrder') == 'asc') {
          order = 'desc';
        }
      }
      $table.data('sortCol', col);
      $table.data('sortOrder', order);
      $table.find('.sort-indicator').addClass('hide');
      $table.find('.sort-indicator.sort-'+col+'-'+order).removeClass('hide');
      var trs = $table.find('tbody tr');
      var pkgs = [];
      var currentTr = [];
      for (var i = 0; i < trs.length; i++) {
        if($(trs[i]).hasClass('package') && currentTr.length > 0) {
          pkgs.push(currentTr);
          currentTr = [];
        }
        currentTr.push(trs[i]);
      }
      pkgs.push(currentTr);
      pkgs.sort(function(a, b) {
        var keyA = $(a[0]).find('td:nth-child('+col+')').text();
        var keyAi = parseInt(keyA);
        if(keyAi>-1) {
          keyA = keyAi;
        }
        var keyB = $(b[0]).find('td:nth-child('+col+')').text();
        var keyBi = parseInt(keyB);
        if(keyBi>-1) {
          keyB = keyBi;
        }
        if (order=='asc') {
            return (keyA > keyB) ? 1 : 0;
        } else {
            return (keyA > keyB) ? 0 : 1;
        }
      });
      var $tbody = $table.find('tbody');
      $tbody.html('');
      for (var i = 0; i < pkgs.length; i++) {
        for (var j = 0; j < pkgs[i].length; j++) {
          $tbody.append(pkgs[i][j]);
        };
      }
      if(!$table.data('showVersions')) {
        $tbody.find('tr.package').removeClass('stripe');
        $tbody.find('tr.package:odd').addClass('stripe');
      }
    }

    $('.btn-sort-packages').click(function(e) {
      var $table = $(this).parents('table');
      $table.find('.btn-more').click();
      sort_table($table, 1);
      e.preventDefault();
    });

    $('.btn-sort-count').click(function(e) {
      var $table = $(this).parents('table');
      $table.find('.btn-more').click();
      sort_table($table, 2);
      e.preventDefault();
    });

    $('#show-advanced-filters').click(function() {
      $('#advanced-filters').removeClass('hide');
      $(this).addClass('hide');
    });

    const observer = new ResizeObserver(entries => {
      for (let entry of entries) {
        const container = entry.target.querySelector('.crash-fn');
        const expander = entry.target.querySelector('.expander');
        const expanded = $(container).hasClass('expanded');
        if (expanded && (container.scrollHeight == expander.scrollHeight)) {
          container.classList.remove('expanded');

          return;
        }
        const showExpander = !expanded && (container.scrollHeight > container.clientHeight);
        const showCollapser = expanded;
        if (showExpander) {
          expander.innerHTML = 'show more';
        }
        else if (showCollapser) {
          expander.innerHTML = 'show less';
        }

        expander.hidden = !(showExpander || showCollapser);
      }
    });

    document.querySelectorAll(".crash-fn-container").forEach(element => {
      expander = element.querySelector('.expander');
      if (expander == null) {
        return;
      }

      expander.addEventListener('click', (event) => {
        element.querySelector('.crash-fn').classList.toggle('expanded');

        event.preventDefault();
      });
      observer.observe(element);
    });
});


function postData(url, data, success) {
  $.ajax({
    type: 'POST',
    contentType: 'application/json',
    url: url,
    data: JSON.stringify(data),
    success: success
  })
}

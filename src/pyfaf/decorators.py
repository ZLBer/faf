# Copyright (C) 2013  ABRT Team
# Copyright (C) 2013  Red Hat, Inc.
#
# This file is part of faf.
#
# faf is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# faf is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with faf.  If not, see <http://www.gnu.org/licenses/>.

import sys
import time
import traceback

__all__ = ["retry"]


# Modified retry decorator with exponential backoff from PythonDecoratorLibrary
def retry(tries, delay=3, backoff=2, verbose=False):
    '''
    Retries a function or method until it returns value.

    Delay sets the initial delay in seconds, and backoff sets the factor by which
    the delay should lengthen after each failure. backoff must be greater than 1,
    or else it isn't really a backoff. tries must be at least 0, and delay
    greater than 0.
    '''

    def deco_retry(f):
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay  # make mutable

            while mtries > 0:
                try:
                    return f(*args, **kwargs)
                except Exception as e:
                    exc_type, exc_value, exc_traceback = sys.exc_info()

                    if verbose:
                        print('Exception occured, retrying in {0} seconds'
                              ' {1}/{2}'.format(mdelay, (tries - mtries + 1),
                                                tries))

                        msg = traceback.format_exception(exc_type, exc_value,
                                                         exc_traceback)

                        if type(msg) == list:
                            msg = ''.join(msg)

                        print(msg)
                    mtries -= 1

                time.sleep(mdelay)
                mdelay *= backoff  # make future wait longer

            raise e  # out of tries

        return f_retry
    return deco_retry
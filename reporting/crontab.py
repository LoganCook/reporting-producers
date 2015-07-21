#!/usr/bin/env python

# pylint: disable=broad-except

# from http://code.activestate.com/recipes/577466-cron-like-triggers/

import time
import datetime
import calendar

DAY_NAMES = zip(('sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'), xrange(7))
MONTH_NAMES = zip(('jan', 'feb', 'mar', 'apr', 'may', 'jun',
                   'jul', 'aug', 'sep', 'oct', 'nov', 'dec'), xrange(1, 13))
MINUTES = (0, 59)
HOURS = (0, 23)
DAYS_OF_MONTH = (1, 31)
MONTHS = (1, 12)
DAYS_OF_WEEK = (0, 6)
FIELD_RANGES = (MINUTES, HOURS, DAYS_OF_MONTH, MONTHS, DAYS_OF_WEEK)
DEFAULT_EPOCH = (1970, 1, 1, 0, 0, 0)
L_FIELDS = (DAYS_OF_WEEK, DAYS_OF_MONTH)

class CronEvent(object):
    def __init__(self, cron, epoch=DEFAULT_EPOCH, epoch_utc_offset=0):
        fields = cron.split(None, 5)
        minutes, hours, dom, months, dow = fields
        dow = dow.replace('7', '0').replace('?', '*')
        dom = dom.replace('?', '*')
        for monthstr, monthnum in MONTH_NAMES:
            months = months.lower().replace(monthstr, str(monthnum))

        for dowstr, downum in DAY_NAMES:
            dow = dow.lower().replace(dowstr, str(downum))

        self.string_tab = [minutes, hours, dom.upper(), months, dow.upper()]
        self.numerical_tab = []

        for field_str, span in zip(self.string_tab, FIELD_RANGES):
            split_field_str = field_str.split(',')
            if len(split_field_str) > 1 and "*" in split_field_str:
                raise ValueError("\"*\" must be alone in a field.")

            unified = set()
            for cron_atom in split_field_str:
                # parse_atom only handles static cases
                for special_char in ('%', '#', 'L', 'W'):
                    if special_char in cron_atom:
                        break
                else:
                    unified.update(parse_atom(cron_atom, span))

            self.numerical_tab.append(unified)

        if self.string_tab[2] == "*" and self.string_tab[4] != "*":
            self.numerical_tab[2] = set()
            
        if len(epoch) == 5:
            y, mo, d, h, m = epoch
            self.epoch = (y, mo, d, h, m, epoch_utc_offset)
        else:
            self.epoch = epoch

    def check_trigger(self, date_tuple, utc_offset=0):
        """
        Returns boolean indicating if the trigger is active at the given time.
        The date tuple should be in the local time. Unless periodicities are
        used, utc_offset does not need to be specified. If periodicities are
        used, specifically in the hour and minutes fields, it is crucial that
        the utc_offset is specified.
        """
        year, month, day, hour, mins = date_tuple
        given_date = datetime.date(year, month, day)
        zeroday = datetime.date(*self.epoch[:3])
        last_dom = calendar.monthrange(year, month)[-1]
        dom_matched = True

        # In calendar and datetime.date.weekday, Monday = 0
        given_dow = (datetime.date.weekday(given_date) + 1) % 7
        first_dow = (given_dow + 1 - day) % 7

        # Figure out how much time has passed from the epoch to the given date
        utc_diff = utc_offset - self.epoch[5]
        mod_delta_yrs = year - self.epoch[0]
        mod_delta_mon = month - self.epoch[1] + mod_delta_yrs * 12
        mod_delta_day = (given_date - zeroday).days
        mod_delta_hrs = hour - self.epoch[3] + mod_delta_day * 24 + utc_diff
        mod_delta_min = mins - self.epoch[4] + mod_delta_hrs * 60

        # Makes iterating through like components easier.
        quintuple = zip(
            (mins, hour, day, month, given_dow),
            self.numerical_tab,
            self.string_tab,
            (mod_delta_min, mod_delta_hrs, mod_delta_day, mod_delta_mon,
                mod_delta_day),
            FIELD_RANGES)

        for value, valid_values, field_str, delta_t, field_type in quintuple:
            # All valid, static values for the fields are stored in sets
            if value in valid_values:
                continue

            # The following for loop implements the logic for context
            # sensitive and epoch sensitive constraints. break statements,
            # which are executed when a match is found, lead to a continue
            # in the outer loop. If there are no matches found, the given date
            # does not match expression constraints, so the function returns
            # False as seen at the end of this for...else... construct.
            for cron_atom in field_str.split(','):
                if cron_atom[0] == '%':
                    if not(delta_t % int(cron_atom[1:])):
                        break

                elif field_type == DAYS_OF_WEEK and '#' in cron_atom:
                    D, N = int(cron_atom[0]), int(cron_atom[2])
                    # Computes Nth occurence of D day of the week
                    if (((D - first_dow) % 7) + 1 + 7 * (N - 1)) == day:
                        break

                elif field_type == DAYS_OF_MONTH and cron_atom[-1] == 'W':
                    target = min(int(cron_atom[:-1]), last_dom)
                    lands_on = (first_dow + target - 1) % 7
                    if lands_on == 0:
                        # Shift from Sun. to Mon. unless Mon. is next month
                        target += 1 if target < last_dom else -2
                    elif lands_on == 6:
                        # Shift from Sat. to Fri. unless Fri. in prior month
                        target += -1 if target > 1 else 2

                    # Break if the day is correct, and target is a weekday
                    if target == day and (first_dow + target - 7) % 7 > 1:
                        break

                elif field_type in L_FIELDS and cron_atom.endswith('L'):
                    # In dom field, L means the last day of the month
                    target = last_dom

                    if field_type == DAYS_OF_WEEK:
                        # Calculates the last occurence of given day of week
                        desired_dow = int(cron_atom[:-1])
                        target = (((desired_dow - first_dow) % 7) + 29)
                        target -= 7 if target > last_dom else 0

                    if target == day:
                        break
            else:
                # See 2010.11.15 of CHANGELOG
                if field_type == DAYS_OF_MONTH and self.string_tab[4] != '*':
                    dom_matched = False
                    continue
                elif field_type == DAYS_OF_WEEK and self.string_tab[2] != '*':
                    # If we got here, then days of months validated so it does
                    # not matter that days of the week failed.
                    return dom_matched

                # None of the expressions matched which means this field fails
                return False

        # Arriving at this point means the date landed within the constraints
        # of all fields; the associated trigger should be fired.
        return True

def parse_atom(parse, minmax):
    """
    Returns a set containing valid values for a given cron-style range of
    numbers. The 'minmax' arguments is a two element iterable containing the
    inclusive upper and lower limits of the expression.

    Examples:
    >>> parse_atom("1-5",(0,6))
    set([1, 2, 3, 4, 5])

    >>> parse_atom("*/6",(0,23))
    set([0, 6, 12, 18])

    >>> parse_atom("18-6/4",(0,23))
    set([18, 22, 0, 4])

    >>> parse_atom("*/9",(0,23))
    set([0, 9, 18])
    """
    parse = parse.strip()
    increment = 1
    if parse == '*':
        return set(xrange(minmax[0], minmax[1] + 1))
    elif parse.isdigit():
        # A single number still needs to be returned as a set
        value = int(parse)
        if value >= minmax[0] and value <= minmax[1]:
            return set((value,))
        else:
            raise ValueError("Invalid bounds: \"%s\"" % parse)
    elif '-' in parse or '/' in parse:
        divide = parse.split('/')
        subrange = divide[0]
        if len(divide) == 2:
            # Example: 1-3/5 or */7 increment should be 5 and 7 respectively
            increment = int(divide[1])

        if '-' in subrange:
            # Example: a-b
            prefix, suffix = [int(n) for n in subrange.split('-')]
            if prefix < minmax[0] or suffix > minmax[1]:
                raise ValueError("Invalid bounds: \"%s\"" % parse)
        elif subrange == '*':
            # Include all values with the given range
            prefix, suffix = minmax
        else:
            raise ValueError("Unrecognized symbol: \"%s\"" % subrange)

        if prefix < suffix:
            # Example: 7-10
            return set(xrange(prefix, suffix + 1, increment))
        else:
            # Example: 12-4/2; (12, 12 + n, ..., 12 + m*n) U (n_0, ..., 4)
            noskips = list(xrange(prefix, minmax[1] + 1))
            noskips+= list(xrange(minmax[0], suffix + 1))
            return set(noskips[::increment])
                            
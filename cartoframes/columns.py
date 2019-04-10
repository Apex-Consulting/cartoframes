# coding=UTF-8

import re


class Column(object):
    MAX_LENGTH = 63
    MAX_COLLISION_LENGTH = MAX_LENGTH - 4
    RESERVED_WORDS = ('ALL', 'ANALYSE', 'ANALYZE', 'AND', 'ANY', 'ARRAY', 'AS', 'ASC', 'ASYMMETRIC', 'AUTHORIZATION',
                      'BETWEEN', 'BINARY', 'BOTH', 'CASE', 'CAST', 'CHECK', 'COLLATE', 'COLUMN', 'CONSTRAINT',
                      'CREATE', 'CROSS', 'CURRENT_DATE', 'CURRENT_ROLE', 'CURRENT_TIME', 'CURRENT_TIMESTAMP',
                      'CURRENT_USER', 'DEFAULT', 'DEFERRABLE', 'DESC', 'DISTINCT', 'DO', 'ELSE', 'END', 'EXCEPT',
                      'FALSE', 'FOR', 'FOREIGN', 'FREEZE', 'FROM', 'FULL', 'GRANT', 'GROUP', 'HAVING', 'ILIKE', 'IN',
                      'INITIALLY', 'INNER', 'INTERSECT', 'INTO', 'IS', 'ISNULL', 'JOIN', 'LEADING', 'LEFT', 'LIKE',
                      'LIMIT', 'LOCALTIME', 'LOCALTIMESTAMP', 'NATURAL', 'NEW', 'NOT', 'NOTNULL', 'NULL', 'OFF',
                      'OFFSET', 'OLD', 'ON', 'ONLY', 'OR', 'ORDER', 'OUTER', 'OVERLAPS', 'PLACING', 'PRIMARY',
                      'REFERENCES', 'RIGHT', 'SELECT', 'SESSION_USER', 'SIMILAR', 'SOME', 'SYMMETRIC', 'TABLE', 'THEN',
                      'TO', 'TRAILING', 'TRUE', 'UNION', 'UNIQUE', 'USER', 'USING', 'VERBOSE', 'WHEN', 'WHERE',
                      'XMIN', 'XMAX', 'FORMAT', 'CONTROLLER', 'ACTION', )

    def __init__(self, name):
        if not name:
            raise ValueError('Column name cannot be null or empty')

        self.name = str(name)
        self.normalize()

    def normalize(self, forbidden_columns=None):
        self._sanitize()
        self.name = self._truncate()

        if forbidden_columns:
            i = 1
            while self.name in forbidden_columns:
                self.name = '{}_{}'.format(self._truncate(length=Column.MAX_COLLISION_LENGTH), str(i))
                i += 1

        return self

    def _sanitize(self):
        self.name = self._slugify(self.name)

        if self._is_reserved() or self._is_unsupported():
            self.name = '_{}'.format(self.name)
        else:
            self.name

    def _is_reserved(self):
        return self.name.upper() in Column.RESERVED_WORDS

    def _is_unsupported(self):
        return not re.match(r'^[a-z_]+[a-z_0-9]*$', self.name)

    def _truncate(self, length=MAX_LENGTH):
        return self.name[:length]

    def _slugify(self, value):
        value = str(value).lower()
        value = re.sub(r'<[^>]+>', '', value)
        value = re.sub(r'[àáâãäåāă]', 'a', value)
        value = re.sub(r'æ', 'ae', value)
        value = re.sub(r'[ďđ]', 'd', value)
        value = re.sub(r'[çćčĉċ]', 'c', value)
        value = re.sub(r'[èéêëēęěĕė]', 'e', value)
        value = re.sub(r'ƒ', 'f', value)
        value = re.sub(r'[ĝğġģ]', 'g', value)
        value = re.sub(r'[ĥħ]', 'h', value)
        value = re.sub(r'[ììíîïīĩĭ]', 'i', value)
        value = re.sub(r'[įıĳĵ]', 'j', value)
        value = re.sub(r'[ķĸ]', 'k', value)
        value = re.sub(r'[łľĺļŀ]', 'l', value)
        value = re.sub(r'[ñńňņŉŋ]', 'n', value)
        value = re.sub(r'[òóôõöøōőŏŏ]', 'o', value)
        value = re.sub(r'œ', 'oe', value)
        value = re.sub(r'ą', 'q', value)
        value = re.sub(r'[ŕřŗ]', 'r', value)
        value = re.sub(r'[śšşŝș]', 's', value)
        value = re.sub(r'[ťţŧț]', 't', value)
        value = re.sub(r'[ùúûüūůűŭũų]', 'u', value)
        value = re.sub(r'ŵ', 'w', value)
        value = re.sub(r'[ýÿŷ]', 'y', value)
        value = re.sub(r'[žżź]', 'z', value)

        value = re.sub(r'&.+?;', '-', value)
        value = re.sub(r'[^a-z0-9 _-]', '-', value).strip().lower()
        value = re.sub(r'\s+', '-', value)
        value = re.sub(r'-+', '-', value)
        value = re.sub(r'-', ' ', value)
        value = re.sub(r' ', '-', value)
        value = re.sub(r'-', '_', value)

        return value


def normalize_names(column_names):
    """Given an arbitrary column name, translate to a SQL-normalized column
        name a la CARTO's Import API will translate to

        Examples
            * 'Field: 2' -> 'field_2'
            * '2 Items' -> '_2_items'
            * 'Unnamed: 0' -> 'unnamed_0',
            * '201moore' -> '_201moore',
            * '201moore' -> '_201moore_1',
            * 'Acadia 1.2.3' -> 'acadia_1_2_3',
            * 'old_soaker' -> 'old_soaker',
            * '_testingTesting' -> '_testingtesting',
            * 1 -> '_1',
            * 1.0 -> '_1_0',
            * 'public' -> 'public',
            * 'SELECT' -> '_select',
            * 'à' -> 'aa',
            * 'aa' -> 'aa_1',
            * '_a' -> '_a',
            * 'longcolumnshouldbesplittedsomehowanditellyouwhereitsgonnabesplittedrightnow' -> \
             'longcolumnshouldbesplittedsomehowanditellyouwhereitsgonnabespli',
            * 'longcolumnshouldbesplittedsomehowanditellyouwhereitsgonnabesplittedrightnow' -> \
             'longcolumnshouldbesplittedsomehowanditellyouwhereitsgonnabe_1',
            * 'all' -> '_all'

        Args:
            column_names (list): List of column names that will be SQL normalized
        Returns:
            list: List of SQL-normalized column names
    """
    result = []
    for column_name in column_names:
        column = Column(column_name).normalize(forbidden_columns=result)
        result.append(column.name)

    return result


def normalize_name(column_name):
    return normalize_names([column_name])[0]

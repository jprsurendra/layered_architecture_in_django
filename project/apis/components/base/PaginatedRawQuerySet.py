from django.db import models
from django.db.models import sql
from django.db.models.query import RawQuerySet
from django.db import connection


class PaginatedRawQuerySet(RawQuerySet):
    def __init__(self, raw_query, raw_count_query=None, **kwargs):
        super(PaginatedRawQuerySet, self).__init__(raw_query, **kwargs)
        self.original_raw_query = raw_query
        self.original_raw_count_query = raw_count_query
        self._result_cache = None
        self._result_count_cache = None

    def __getitem__(self, k):
        """
        Retrieves an item or slice from the set of results.
        """
        if not isinstance(k, (slice, int,)):
            raise TypeError
        assert ((not isinstance(k, slice) and (k >= 0)) or
                (isinstance(k, slice) and (k.start is None or k.start >= 0) and
                 (k.stop is None or k.stop >= 0))), \
            "Negative indexing is not supported."

        if self._result_cache is not None:
            return self._result_cache[k]

        if isinstance(k, slice):
            qs = self._clone()
            if k.start is not None:
                start = int(k.start)
            else:
                start = None
            if k.stop is not None:
                stop = int(k.stop)
            else:
                stop = None
            qs.set_limits(start, stop)
            return qs

        qs = self._clone()
        qs.set_limits(k, k + 1)
        return list(qs)[0]

    def __iter__(self):
        self._fetch_all()
        return iter(self._result_cache)

    def count(self):
        # if self._result_cache is not None:
        #     print("--- --- len(self._result_cache) --- ---- ")
        #     return len(self._result_cache)
        # return self.model.objects.count()

        if self._result_count_cache is None:
            cursor = connection.cursor()
            cursor.execute(self.original_raw_count_query)
            row = cursor.fetchall()
            self._result_count_cache = row[0][0]

        return self._result_count_cache
        # raw_count_query = sql.RawQuery(sql=self.original_raw_count_query, using=self.db, params=self.params)
        # print(self.query)
        # return len(raw_count_query)

    def set_limits(self, start, stop):
        limit_offset = ''

        new_params = tuple()
        if start is None:
            start = 0
        elif start > 0:
            new_params += (start,)
            limit_offset = ' OFFSET %s'
        if stop is not None:
            new_params = (stop - start,) + new_params
            limit_offset = 'LIMIT %s' + limit_offset

        self.params = self.params + new_params
        self.raw_query = self.original_raw_query + limit_offset
        self.query = sql.RawQuery(sql=self.raw_query, using=self.db, params=self.params)

    def _fetch_all(self):
        if self._result_cache is None:
            self._result_cache = list(super().__iter__())

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.model.__name__)

    def __len__(self):
        self._fetch_all()
        return len(self._result_cache)

    def _clone(self):
        clone = self.__class__(raw_query=self.raw_query, model=self.model, using=self._db, hints=self._hints,
                               query=self.query, params=self.params, translations=self.translations)
        return clone
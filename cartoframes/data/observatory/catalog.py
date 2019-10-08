from __future__ import absolute_import

from .category import Category
from .country import Country
from .dataset import Dataset


class Catalog(object):
    """Data Observatory Catalog"""

    @property
    def countries(self):
        """Get all the countries in the Catalog

        Returns:
            :py:class:`Categories <cartoframes.data.observatory.Countries>`

        """

        return Country.get_all()

    @property
    def categories(self):
        """Get all the categories in the Catalog

        Returns:
            :py:class:`Categories <cartoframes.data.observatory.Categories>`

        """

        return Category.get_all()

    @classmethod
    def datasets(self, credentials):
        """Get all the datasets in the Catalog

        Args:
            credentials (:py:class:`Credentials <cartoframes.auth.Credentials>`):
                A :py:class:`Credentials <cartoframes.auth.Credentials>`
                instance can be used in place of a `username`|`base_url` / `api_key` combination.

        Returns:
            :py:class:`Datasets <cartoframes.data.observatory.Datasets>`

        """

        return Dataset.get_all(credentials)

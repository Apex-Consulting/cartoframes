from geopandas import GeoDataFrame

from ..utils.geom_utils import generate_index, generate_geometry


class CartoDataFrame(GeoDataFrame):
    def __init__(self, *args, **kwargs):
        """
        A CartoDataFrame object is a
        `geopandas.GeoDataFrame <http://geopandas.org/reference/geopandas.GeoDataFrame.html>`_
        that has a column with geometry. It extends the GeoDataFrame object to read and
        write data from CARTO, adding wrappers when necessary.
        """

        super(CartoDataFrame, self).__init__(*args, **kwargs)

    @staticmethod
    def from_carto(*args, **kwargs):
        """
        Alternate constructor to create a CartoDataFrame from a table or SQL query in CARTO.
        Equivalent to :py:meth:`read_carto <cartoframes.io.read_carto>`.

        Examples:

            Using a table name:

            .. code::

                from cartoframes import CartoDataFrame

                cdf = CartoDataFrame.from_carto('table_name')

            Using a SQL query:

            .. code::

                from cartoframes import CartoDataFrame

                cdf = CartoDataFrame.from_carto('SELECT * FROM table_name WHERE value > 100')
        """

        from ..io.carto import read_carto
        return read_carto(*args, **kwargs)

    @classmethod
    def from_file(cls, filename, **kwargs):
        """
        Alternate constructor to create a CartoDataFrame from a file.
        Extends from the GeoDataFrame.from_file method.

        Examples:

            .. code::

                from cartoframes import CartoDataFrame

                cdf = CartoDataFrame.from_file('nybb.shp')
        """

        gdf = GeoDataFrame.from_file(filename, **kwargs)
        return cls(gdf)

    @classmethod
    def from_features(cls, features, **kwargs):
        """
        Alternate constructor to create a CartoDataframe from GeoJSON features.
        Extends from the GeoDataFrame.from_features method.

        Examples:

            .. code::

                from cartoframes import CartoDataFrame

                cdf = CartoDataFrame.from_features('nybb.shp')
        """

        gdf = GeoDataFrame.from_features(features, **kwargs)
        return cls(gdf)

    def to_carto(self, *args, **kwargs):
        """
        Upload a CartoDataFrame to CARTO.
        Equivalent to :py:meth:`to_carto <cartoframes.io.to_carto>`.

        Examples:

            .. code::
                from cartoframes import CartoDataFrame

                cdf = CartoDataFrame.from_file('nybb.shp')
                cdf.to_carto(if_exists='replace')
        """

        from ..io.carto import to_carto
        return to_carto(self, *args, **kwargs)

    def convert(self, index_column=None, geom_column=None, lnglat_columns=None,
                drop_index=True, drop_geom=True, drop_lnglat=True):
        """ For internal usage only.
        Tries to decode the geometry automatically as a `shapely https://pypi.org/project/Shapely/_.`
        object by looking for coordinates in columns.

        Args:
            index_column (str, optional):
                Name of the index column. If it is `None`, it is generated automatically.
            geom_column (str, optional):
                Name of the geometry column to be used to generate the decoded geometry.
                If it is None, it tries to find common geometry column names, but if there is
                no geometry column it will leave it empty.
            lnglat_columns ([str, str], optional):
                Tuple with the longitude and latitude column names to be used to generate
                the decoded geometry.
            drop_index (bool, optional):
                Defaults to True. Removes the index column.
            drop_geom (bool, optional):
                Defaults to True. Removes the geometry column.
            drop_lnglat (bool, optional):
                Defaults to True. Removes the lnglat column.

        Returns:
            The CartoDataFrame itself

        Examples:

            Decode the geometry automatically:

            .. code::
                from cartoframes import CartoDataFrame

                cdf = CartoDataFrame.from_file('filename.csv').convert()

            Passing the geometry column explicitly:

            .. code::

                from cartoframes import CartoDataFrame

                cdf = CartoDataFrame.from_file('filename.csv')
                cdf.convert(geom_column='my_geom_column')

            Passing lnglat_columns explicitly:

            .. code::

                from cartoframes import CartoDataFrame

                cdf = CartoDataFrame.from_file('filename.csv')
                cdf.convert(lnglat_columns=['longitude', 'latitude'])

            Passing the index column explicitly:

            .. code::

                from cartoframes import CartoDataFrame

                cdf = CartoDataFrame.from_file('filename.csv')
                cdf.convert(index_column='my_index')

        """

        generate_index(self, index_column, drop_index)
        generate_geometry(self, geom_column, lnglat_columns, drop_geom, drop_lnglat)
        return self

    def viz(self, *args, **kwargs):
        """
        Creates a :py:class:`Map <cartoframes.viz.Map>`. visualization
        """

        from ..viz import Map, Layer
        return Map(Layer(self, *args, **kwargs))

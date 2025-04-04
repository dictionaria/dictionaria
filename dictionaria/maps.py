"""Custom maps for dictionaria."""

from clld.web.maps import Map


class LanguagesMap(Map):
    """Custom language map."""

    def get_options(self):
        """Slightly adjust the icon size."""
        return {'icon_size': 20}


def includeme(config):
    """Do pyramid's mighty metaprogramming magic."""
    config.register_map('languages', LanguagesMap)

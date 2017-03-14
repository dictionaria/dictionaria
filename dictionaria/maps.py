from clld.web.maps import Map


class LanguagesMap(Map):
    def get_options(self):
        return {'icon_size': 20}


def includeme(config):
    config.register_map('languages', LanguagesMap)

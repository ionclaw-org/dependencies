from conan import ConanFile


class DepsConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    requires = "poco/1.14.2"

    def requirements(self):
        self.requires("openssl/3.6.1", override=True)

    def configure(self):
        self.options["poco"].shared = False
        self.options["poco"].enable_netssl = True
        self.options["poco"].enable_crypto = True
        self.options["poco"].enable_net = True
        self.options["poco"].enable_util = True
        self.options["poco"].enable_xml = True
        self.options["poco"].enable_zip = True
        self.options["poco"].enable_json = False
        self.options["poco"].enable_data = False
        self.options["poco"].enable_data_sqlite = False
        self.options["poco"].enable_data_mysql = False
        self.options["poco"].enable_data_postgresql = False
        self.options["poco"].enable_data_odbc = False
        self.options["poco"].enable_encodings = False
        self.options["poco"].enable_mongodb = False
        self.options["poco"].enable_redis = False
        self.options["poco"].enable_jwt = False
        self.options["poco"].enable_prometheus = False
        self.options["poco"].enable_activerecord = False
        self.options["poco"].enable_apacheconnector = False
        self.options["poco"].enable_netssl_win = False
        self.options["poco"].enable_pdf = False
        self.options["poco"].enable_sevenzip = False
        self.options["poco"].enable_pagecompiler = False
        self.options["poco"].enable_pagecompiler_file2page = False
        self.options["poco"].enable_pocodoc = False
        self.options["poco"].enable_cppparser = False

        if self.settings.os in ("iOS", "tvOS", "watchOS", "visionOS"):
            self.options["poco"].enable_fork = False
            self.options["openssl"].no_apps = True
            self.options["pcre2"].build_pcre2grep = False

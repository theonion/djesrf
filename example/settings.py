ROOT_URLCONF = "example.app.urls"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "default",
    }
}

INSTALLED_APPS = (
    "djes",
    "djesrf",
    "example.app",
)

SECRET_KEY = "wow much secure"

MIDDLEWARE_CLASSES = (
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware"
)

ES_INDEX = "djesrf-example"

ES_INDEX_SETTINGS = {
    "djesrf-example": {
        "index": {
            "number_of_replicas": 1,
            "analysis": {
                "filter": {
                    "autocomplete_filter": {
                        "type": "edge_ngram",
                        "min_gram": 1,
                        "max_gram": 20
                    }
                },
                "analyzer": {
                    "autocomplete": {
                        "type":      "custom",
                        "tokenizer": "standard",
                        "filter": [
                            "lowercase",
                            "autocomplete_filter"
                        ]
                    }
                }
            }
        },
    }
}

ES_CONNECTIONS = {
    "default": {
        "hosts": "localhost"
    }
}

# TUD Assistance Backbone

The TUD Assistance Backbone (TAB) is a software component that can be used to analyze learning process data in the
form of xAPI statements and provide feedback to learners' interactions and assistance and suggestions with regard
to the user's learning state and the corresponding learning content. Four kinds of assistance types are supported:

1. *Cooperative assistance* provide assistance according to cooperative processes.
2. *Informational feedback* provide information about the learner, the learning process or the learning content when
actively requested.
3. *Proactive assistance* provide assistance that is appropriate to the learning process when actively requested.
4. *Reactive assistance* provide assistance that is appropriate to the learning process because of the learner's state.

## Prerequisites

To be able to run the project locally, `Python` version `3.10` is required. The required dependencies can be
installed by running:

```bash
pip install -r requirements.txt
```

In addition, a MongoDB is required which can be started by executing:

```bash
docker compose up -d mongo && docker compose up -d mongo_init
```

Furthermore, the application must be configured using environment variables before start:

| Name                           | Description                                                                                                                                                                                                    | Default value                        |
|--------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------|
| CORS_ALLOWED_ORIGINS           | A list of origins for which cross-origin requests are allowed from a browser, separated with comma. Example: `http://localhost:3000,https://tu-dresden.de`                                                     |                                      |
| DEBUG                          | Whether the debug mode should be enabled or not.                                                                                                                                                               | False                                |
| DISABLED_ASSISTANCE_TYPES      | Comma-separated list of the keys of assistance types that should not be provided. The existing assistance types can be requested by calling the `/assistance-type` endpoint after the application was started. |                                      |
| ENVIRONMENT_FILE_PATH          | The path to the file environment variables should be loaded from.                                                                                                                                              | tab.env                              |
| HOST                           | The host the application should be started on.                                                                                                                                                                 | 0.0.0.0                              |
| INTERNATIONALIZATION_FILE_PATH | The path to the file, where different localizations are located.                                                                                                                                               | locale/                              |
| JWT_SECRET_KEY                 | The secret key for JWT encoding and decoding, has to be the same as set for the TUD TAS Backend.                                                                                                               | secret                               |
| MONGO_DATABASE                 | The MongoDB to connect to.                                                                                                                                                                                     | tab_db                               |
| MONGO_HOST                     | The host of the MongoDB to connect to.                                                                                                                                                                         | 127.0.0.1                            |
| MONGO_PORT                     | The port of the MongoDB to connect to.                                                                                                                                                                         | 27017                                |
| MONGO_REPLICA_SET              | The name of the MongoDB replica set to connect to.                                                                                                                                                             |                                      |
| MONGO_TRANSACTIONS_SUPPORTED   | Whether transactions are supported by the MongoDB or not. Can only be set to `True` if a MongoDB replica set is used.                                                                                          | True                                 |
| OLLAMA_URL                     | The URL of the Ollama instance to work with.                                                                                                                                                                   | https://ollama.com                   |
| PORT                           | The port the application should be delivered on.                                                                                                                                                               | 8000                                 |

When developing locally, it may be helpful to copy the `sample.env` file, rename it to `tab.env` and adjust the values
of the environment variables in it. When starting the application, the environment variables from the `tab.env` file are
automatically taken into account.

## Run

The project can be started by running:

```bash
python main.py
```

The API can then be accessed at <http://127.0.0.1:8000>. The OpenAPI specification of the API can be obtained by
calling <http://127.0.0.1:8000/docs>. For testing purposes a JWT can be requested by executing:

```bash
PYTHONPATH=$PWD:$PYTHONPATH python ./dev/scripts/createJwt.py
```

### Run Docker Compose setup

All required images can be built and the corresponding containers can be started by executing:

```bash
docker-compose -f docker-compose-local.yml up # --build -d
```

## Development

The component is developed using a spec-first API development approach. The specification file can be found in 
`./spec/api.yaml`. In order to make changes that influence the REST API this specification has to be adjusted first.
Afterward, the updated code can be generated by executing

```bash
./dev/scripts/generateCodeFromOpenApiSpec.sh
```

The generated code can be found in `./gen`. The required files have to be moved manually.

## License

This plugin is licensed under the GPL v3 License (for further information, see [LICENSE](LICENSE)).

## Libraries used

| Name              | Version     | License                              | URL                                                               | Description                                                                                 |
|-------------------|-------------|--------------------------------------|-------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| PyJWT             | 2.8.0       | MIT License                          | https://github.com/jpadilla/pyjwt                                 | JSON Web Token implementation in Python                                                     |
| PyYAML            | 6.0.1       | MIT License                          | https://pyyaml.org/                                               | YAML parser and emitter for Python                                                          |
| SQLAlchemy        | 2.0.28      | MIT License                          | https://www.sqlalchemy.org                                        | Database Abstraction Library                                                                |
| StompWS           |             | MIT License                          | https://github.com/akshayeshenoi/StompWS                          | A Python library that enables simple STOMP communication over WebSockets.                   |
| annotated-types   | 0.6.0       | MIT License                          | https://github.com/annotated-types/annotated-types                | Reusable constraint types to use with typing.Annotated                                      |
| anyio             | 4.3.0       | MIT License                          | https://anyio.readthedocs.io/en/stable/versionhistory.html        | High level compatibility layer for multiple asynchronous event loop implementations         |
| certifi           | 2024.2.2    | Mozilla Public License 2.0 (MPL 2.0) | https://github.com/certifi/python-certifi                         | Python package for providing Mozilla's CA Bundle.                                           |
| click             | 8.1.7       | BSD License                          | https://palletsprojects.com/p/click/                              | Composable command line interface toolkit                                                   |
| croniter          | 1.4.1       | MIT License                          | http://github.com/kiorky/croniter                                 | croniter provides iteration for datetime object with cron like format                       |
| dnspython         | 2.6.1       | ISC License (ISCL)                   | https://www.dnspython.org                                         | DNS toolkit                                                                                 |
| dotmap            | 1.3.30      | MIT License                          | https://github.com/drgrib/dotmap                                  | Production ready implementation of a dictionary allowing dot style access to stored values. |
| exceptiongroup    | 1.2.0       | MIT License                          | https://github.com/agronholm/exceptiongroup/blob/main/CHANGES.rst | Backport of PEP 654 (exception groups)                                                      |
| fastapi           | 0.109.0     | MIT License                          | https://github.com/tiangolo/fastapi                               | FastAPI framework, high performance, easy to learn, fast to code, ready for production      |
| fastapi-utilities | 0.1.3.1     | MIT License                          | https://github.com/priyanshu-panwar/fastapi-utilities             | Reusable utilities for FastAPI                                                              |
| h11               | 0.14.0      | MIT License                          | https://github.com/python-hyper/h11                               | A pure-Python, bring-your-own-I/O implementation of HTTP/1.1                                |
| httpcore          | 1.0.4       | BSD License                          | https://www.encode.io/httpcore/                                   | A minimal low-level HTTP client.                                                            |
| httpx             | 0.26.0      | BSD License                          | https://github.com/encode/httpx                                   | The next generation HTTP client.                                                            |
| idna              | 3.6         | BSD License                          | https://github.com/kjd/idna                                       | Internationalized Domain Names in Applications (IDNA)                                       |
| loguru            | 0.7.2       | MIT License                          | https://github.com/Delgan/loguru                                  | Python logging made (stupidly) simple                                                       |
| mongomock         | 4.1.2       | BSD License                          | https://github.com/mongomock/mongomock                            | Fake pymongo stub for testing simple MongoDB-dependent code                                 |
| numpy             | 1.26.4      | BSD License                          | https://numpy.org                                                 | Fundamental package for array computing in Python                                           |
| pandas            | 2.1.4       | BSD License                          | https://pandas.pydata.org                                         | Powerful data structures for data analysis, time series, and statistics                     |
| py-fibonacci      | 0.5.2       | MIT License                          | https://github.com/pydatageek/py-fibonacci                        | Generates Fibonacci series with an end number OR a length argument.                         |
| pydantic          | 2.5.2       | MIT License                          | https://github.com/pydantic/pydantic                              | Data validation using Python type hints                                                     |
| pydantic_core     | 2.14.5      | MIT License                          | https://github.com/pydantic/pydantic-core                         |                                                                                             |
| pyi18n-v2         | 1.2.1       | MIT License                          | https://github.com/sectasy0/pyi18n                                | Simple and easy to use internationalizationlibrary inspired by Ruby i18n                    |
| pymongo           | 4.6.1       | Apache Software License              | http://github.com/mongodb/mongo-python-driver                     | Python driver for MongoDB <http://www.mongodb.org>                                          |
| pymongo-schema    | 0.4.1       | GNU General Public License v3.0      | https://github.com/pajachiet/pymongo-schema                       | A schema analyser for MongoDB written in Python                                             | 
| pytest            | 7.2.2       | MIT License                          | https://github.com/pytest-dev/pytest                              | pytest: simple powerful testing with Python                                                 |
| python-dateutil   | 2.9.0.post0 | Apache Software License; BSD License | https://github.com/dateutil/dateutil                              | Extensions to the standard Python datetime module                                           |
| python-dotenv     | 1.0.0       | BSD License                          | https://github.com/theskumar/python-dotenv                        | Read key-value pairs from a .env file and set them as environment variables                 |
| pytz              | 2024.1      | MIT License                          | http://pythonhosted.org/pytz                                      | World timezone definitions, modern and historical                                           |
| requests          | 2.28.1      | Apache Software License              | https://github.com/psf/requests                                   | Python HTTP for Humans.                                                                     |
| six               | 1.16.0      | MIT License                          | https://github.com/benjaminp/six                                  | Python 2 and 3 compatibility utilities                                                      |
| sniffio           | 1.3.1       | Apache Software License; MIT License | https://github.com/python-trio/sniffio                            | Sniff out which async library your code is running under                                    |
| starlette         | 0.35.1      | BSD License                          | https://github.com/encode/starlette                               | The little ASGI library that shines.                                                        |
| testcontainers    | 4.6.0       | Apache Software License              | https://github.com/testcontainers/testcontainers-python           | Python library for throwaway instances of anything that can run in a Docker container       |
| typing_extensions | 4.10.0      | Python Software Foundation License   | https://github.com/python/typing_extensions                       | Backported and Experimental Type Hints for Python 3.8+                                      |
| tzdata            | 2024.1      | Apache Software License              | https://github.com/python/tzdata                                  | Provider of IANA time zone data                                                             |
| uuid              | 1.30        | Python Software Foundation License   | http://zesty.ca/python/                                           | UUID object and generation functions                                                        |
| uvicorn           | 0.24.0      | BSD License                          | https://www.uvicorn.org/                                          | The lightning-fast ASGI server.                                                             |
| websocket-client  | 1.7.0       | Apache Software License              | https://github.com/websocket-client/websocket-client.git          | WebSocket client for Python with low level API options                                      |
| websockets        | 12.0        | BSD License                          | https://github.com/python-websockets/websockets                   | An implementation of the WebSocket Protocol (RFC 6455 & 7692)                               |

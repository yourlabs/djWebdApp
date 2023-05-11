FROM yourlabs/blockchain

ENV DJANGO_SETTINGS_MODULE=djwebdapp_demo.settings
EXPOSE 8000

WORKDIR /app

COPY setup.py README.rst /app/

RUN mkdir -p /app/src && pip install --editable /app[all]
COPY src /app/src
RUN pip install --no-deps --editable /app
COPY djwebdapp_demo /app/djwebdapp_demo
COPY manage.py /app

USER app

CMD bash -c "py.test -sv"

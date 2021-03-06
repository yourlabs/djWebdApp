FROM yourlabs/python-arch

ENV DJANGO_SETTINGS_MODULE=djwebdapp_demo.settings
ENV PYTHONIOENCODING=UTF-8 PYTHONUNBUFFERED=1
EXPOSE 8000

RUN pacman -Syu --noconfirm vim libsodium libsecp256k1 && rm -rf /var/cache/pacman/pkg
RUN useradd --home-dir /app --uid 1000 app && mkdir -p /app && chown -R app /app
RUN pip install wheel
# until release of
RUN pip install https://github.com/shmpwk/setuptools-markdown/archive/refs/heads/patch-1.zip
RUN pip install django-rest-framework
WORKDIR /app

COPY setup.py README.rst /app/
# run a first dependency install prior to moving code that would invalidate the
# layer
RUN mkdir /app/src && pip install --editable /app[all]
COPY src /app/src
RUN pip install --no-deps --editable /app
COPY djwebdapp_demo /app/djwebdapp_demo
COPY manage.py /app

USER app

CMD bash -c "py.test -sv"

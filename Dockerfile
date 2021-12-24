FROM yourlabs/python-arch

ENV DJANGO_SETTINGS_MODULE=djwebdapp_demo.settings
ENV PYTHONIOENCODING=UTF-8 PYTHONUNBUFFERED=1
EXPOSE 8000

RUN pacman -Syu --noconfirm vim libsodium libsecp256k1 && rm -rf /var/cache/pacman/pkg
RUN useradd --home-dir /app --uid 1000 app && mkdir -p /app && chown -R app /app
RUN pip install djcli wheel
WORKDIR /app

COPY setup.py README.rst /app/
COPY src /app/src
RUN pip install --editable /app[all]
COPY djwebdapp_demo /app/djwebdapp_demo
COPY manage.py /app

USER app

CMD bash -c "py.test -sv"

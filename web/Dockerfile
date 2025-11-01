FROM python
RUN pip install pymongo
RUN pip install netmiko
RUN pip install flask
COPY  ./static /home/myapp/static/
COPY  ./templates /home/myapp/templates/
COPY  app.py /home/myapp/
COPY  check.py /home/myapp/
COPY  router_actions.py /home/myapp/
EXPOSE 8080
CMD python3 /home/myapp/app.py

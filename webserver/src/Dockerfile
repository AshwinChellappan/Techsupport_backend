#
# NOTE: THIS DOCKERFILE IS INSPIRED BY https://github.com/TadeoRubio/python-pyodbc-msodbcsql17/blob/master/Dockerfile


# Using the official Python image, Tag 3.11.3-slim-buster
FROM python:3.11.3-slim-buster as base

# UPGRADE pip3
RUN pip3 install --upgrade pip

# update apt-get
RUN apt-get update

# get curl
RUN apt-get update -y && apt-get install -y gcc curl gnupg build-essential

# PYODBC DEPENDENCES
RUN apt-get install -y tdsodbc unixodbc-dev
RUN apt install unixodbc-bin -y
RUN apt-get clean -y

# DEPENDECES FOR DOWNLOAD ODBC DRIVER
RUN apt-get install apt-transport-https 
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list
RUN apt-get update

# INSTALL ODBC DRIVER
RUN ACCEPT_EULA=Y apt-get install msodbcsql18 --assume-yes

# CONFIGURE ENV FOR /bin/bash TO USE MSODBCSQL17
RUN echo 'export PATH="$PATH:/opt/mssql-tools/bin"' >> ~/.bash_profile 
RUN echo 'export PATH="$PATH:/opt/mssql-tools/bin"' >> ~/.bashrc 


FROM base

WORKDIR /work

EXPOSE 5174


COPY . .
RUN pip install -r requirements.txt

CMD ["uvicorn", "src.asgi:app", "--host", "0.0.0.0", "--port", "5174"]

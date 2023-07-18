## Bootstrap

### Install dependencies

Install the openbabel dependency on your system

```shell
sudo apt-get openbabel
```

Create a virtualenv and install the python dependencies

```shell
pip install -r requirements.txt
```

## Running the project

```shell
uvicorn server:app --reload
```



## Todo

- [x] setup
- [x] rota que recebe um file e retorna o resultado do processamento
- [ ] subir arquivo pro dropbox e retornar o link
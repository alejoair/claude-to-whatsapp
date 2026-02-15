# Guía de Publicación en PyPI

## Configuración de Credenciales

### 1. Crear cuenta en PyPI

1. Ve a [pypi.org/account/register/](https://pypi.org/account/register/)
2. Regístrate o inicia sesión
3. Verifica tu email para confirmar

### 2. Crear API Token

1. Ve a [pypi.org/manage/account/](https://pypi.org/manage/account/)
2. Haz clic en **"Add API token"**
3. Agrega una descripción (ej: "Claude Code desde localhost")
4. Selecciona el scope: `Entire account` (para poder publicar)
5. Copia el token generado

### 3. Configurar ~/.pypirc

Opción A: Usar Twine (recomendado)

```bash
pip install twine
twine configure __token__
# Pega tu API token aquí
```

Opción B: Variables de entorno

```bash
export TWINE_USERNAME="tu_usuario_pypi"
export TWINE_PASSWORD="tu_api_token"
```

### 4. Formato correcto de ~/.pypirc

```ini
[pypi]
  username = __token__
  password = pypi-AgEIcHlwaS5vcmcCJGQyOGMxNjQyLWMwOTEtNGE4Mi04ZTc0LTUyNmZmMGFkMWQzOA...
```

**⚠️ IMPORTANTE:** El token de PyPI expira después de cierto tiempo (por defecto 1 año), así que usar `__token__` es más seguro y flexible.

## Proceso de Publicación

### 1. Preparar el paquete

Desde el directorio del proyecto:

```bash
# Asegúrate de que la versión sea nueva
# Editar pyproject.toml si es necesario
```

### 2. Construir el paquete

```bash
python -m build
```

### 3. Publicar en PyPI

```bash
twine upload dist/*
```

## Archivos clave del proyecto

1. **`pyproject.toml`** - Metadatos del paquete
2. **`setup.py`** - Configuración clásica (opcional)
3. **`README.md`** - Documentación del paquete (PyPI la mostrará)

## Seguridad

- **NUNCA** expongas tu token en texto plano
- **Siempre** usa `__token__` como username
- El token expira después de 1 año (por defecto)

## Recursos

- [Documentación de PyPI](https://pypi.org/help/)
- [Guía de Twine](https://twine.readthedocs.io/en/stable/#configuration)
- [Documentación de pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)

## Ejemplo completo

```bash
# 1. Instalar Twine
pip install twine

# 2. Configurar credenciales
twine configure __token__
# Pega tu API token aquí

# 3. Verificar configuración
cat ~/.pypirc

# 4. Construir el paquete
python -m build

# 5. Publicar
twine upload dist/*
```

## Notas

- El primer intento de publicación puede requerir revisión manual
- Asegúrate de que el nombre del paquete en `pyproject.toml` sea único
- Verifica que `README.md` exista en el raíz del proyecto

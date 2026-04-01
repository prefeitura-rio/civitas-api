"""
Evita carregar Infisical/Redis ao importar `app` nos testes unitários locais.
Deve ser o primeiro módulo a registrar stubs (pytest carrega conftest antes dos testes).
"""

import sys
import types

if "app.redis_cache" not in sys.modules:
    _rc = types.ModuleType("app.redis_cache")
    _rc.cache = object()
    sys.modules["app.redis_cache"] = _rc

if "app.config" not in sys.modules:
    sys.modules["app.config"] = types.SimpleNamespace(
        TIMEZONE="America/Sao_Paulo",
    )

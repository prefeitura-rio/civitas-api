# Testing

## 🎯 **Performance Tests (CI/CD)**
```bash
poetry run pytest tests/performance/ -v    # Testes async - trava deploy se falhar
```

## 🧪 **Unit Tests**
```bash
poetry run pytest tests/unit/ -v    # Testa lógica de negócio
```

## � **Todos os Testes**
```bash
poetry run pytest -v    # Roda tudo
```

## 📁 **Estrutura**
```
tests/
├── performance/        # Testes de performance async
│   └── test_async_db_performance.py
└── unit/              # Testes unitários (lógica de negócio)
    ├── test_cars_path.py
    └── test_cars_plates.py
```

**Simples assim!** 🎉

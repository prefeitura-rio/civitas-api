#!/usr/bin/env python3
"""
Script para testar o endpoint de PDF em staging
"""

import requests
import json

def test_staging_pdf():
    """
    Testa o endpoint de PDF em staging
    """
    # URL base de staging
    base_url = "https://staging.api.civitas.rio"
    
    # Credenciais
    username = "15164636760"
    password = "sy45hsSoiOCf5WkLIB2dNhIv2nIruuPPgyGPDaNoC4hWrcooQCxKhqiyU4MG"
    
    # 1. Fazer login para obter token
    print("🔐 Fazendo login...")
    login_data = {
        "username": username,
        "password": password
    }
    
    login_response = requests.post(
        f"{base_url}/auth/token",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if login_response.status_code != 200:
        print(f"❌ Erro no login: {login_response.status_code}")
        print(f"Resposta: {login_response.text}")
        return
    
    token_data = login_response.json()
    access_token = token_data.get("access_token")
    
    if not access_token:
        print("❌ Token não encontrado na resposta")
        print(f"Resposta: {token_data}")
        return
    
    print(f"✅ Login realizado com sucesso!")
    print(f"Token: {access_token[:50]}...")
    
    # 2. Testar endpoint de PDF
    print("\n📄 Testando endpoint de PDF...")
    
    pdf_payload = {
        "n_plates": 1000000000,
        "n_minutes": 3,
        "keep_buses": False,
        "report_title": "Relatório de identificação de veículos",
        "min_different_targets": 2,
        "requested_plates_data": [
            {
                "end": "2025-09-01T23:59:00",
                "plate": "LMJ0J34",
                "start": "2025-08-25T00:00:00"
            },
            {
                "end": "2025-09-01T23:59:00",
                "plate": "LTK7D75",
                "start": "2025-08-25T00:00:00"
            }
        ]
    }
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    pdf_response = requests.post(
        f"{base_url}/pdf/multiple-correlated-plates",
        json=pdf_payload,
        headers=headers
    )
    
    print(f"Status: {pdf_response.status_code}")
    print(f"Headers: {dict(pdf_response.headers)}")
    
    if pdf_response.status_code == 200:
        print("✅ PDF gerado com sucesso!")
        
        # Salvar o arquivo
        with open("staging_pdf_response.zip", "wb") as f:
            f.write(pdf_response.content)
        
        print(f"📁 Arquivo salvo como: staging_pdf_response.zip")
        print(f"📊 Tamanho: {len(pdf_response.content)} bytes")
        
        # Verificar se é um ZIP válido
        if pdf_response.content.startswith(b'PK'):
            print("✅ Arquivo é um ZIP válido!")
        else:
            print("⚠️ Arquivo não parece ser um ZIP válido")
            print(f"Primeiros bytes: {pdf_response.content[:20]}")
            
    else:
        print(f"❌ Erro ao gerar PDF: {pdf_response.status_code}")
        print(f"Resposta: {pdf_response.text}")

if __name__ == "__main__":
    test_staging_pdf()


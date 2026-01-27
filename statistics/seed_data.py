import pandas as pd
import numpy as np
from faker import Faker
import psycopg2
from psycopg2 import extras
from datetime import datetime, timedelta
import random

# CONFIGURAÇÕES DE CONEXÃO PURA
DB_PARAMS = {
    "host": "localhost",
    "database": "dev_db",
    "user": "dev_user",
    "password": "cygnusX-1book2",
    "port": "5432"
}


def generate_financial_data(n_leads=3000):
    print("🚀 Iniciando geração de dados...")
    fake = Faker('pt_BR')

    leads_data = []
    purchases_data = []

    channels = {
        'Google_Ads': {'conv_rate': 0.15, 'avg_ticket': 210, 'fraud_rate': 0.05},
        'Facebook_Ads': {'conv_rate': 0.08, 'avg_ticket': 150, 'fraud_rate': 0.12},
        'Organic_Search': {'conv_rate': 0.04, 'avg_ticket': 350, 'fraud_rate': 0.02},
        'Email_Marketing': {'conv_rate': 0.22, 'avg_ticket': 120, 'fraud_rate': 0.01}
    }

    for _ in range(n_leads):
        lead_id = fake.uuid4()
        channel = random.choice(list(channels.keys()))
        test_group = random.choice(['Control', 'Treatment'])
        created_at = fake.date_time_between(start_date='-60d', end_date='now')

        leads_data.append((
            lead_id, fake.name(), channel, test_group,
            random.choice(['mobile', 'desktop']), created_at
        ))

        if random.random() < channels[channel]['conv_rate']:
            purchase_date = created_at + timedelta(days=random.randint(0, 5))
            if purchase_date <= datetime.now():
                status = 'approved'

                if random.random() < channels[channel]['fraud_rate']:
                    status = 'rejected'

                purchases_data.append((
                    fake.uuid4(), lead_id,
                    round(np.random.normal(channels[channel]['avg_ticket'], 30), 2),
                    status, purchase_date
                ))

    try:
        # Conexão Nativa
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        print("📥 Gravando tabelas no dev_db...")

        # 1. Criar Tabelas
        cur.execute("DROP TABLE IF EXISTS purchases CASCADE;")
        cur.execute("DROP TABLE IF EXISTS leads CASCADE;")

        cur.execute("""
            CREATE TABLE leads (
                lead_id UUID PRIMARY KEY,
                name TEXT,
                channel TEXT,
                test_group TEXT,
                device TEXT,
                created_at TIMESTAMP
            );
        """)

        cur.execute("""
            CREATE TABLE purchases (
                purchase_id UUID PRIMARY KEY,
                lead_id UUID REFERENCES leads(lead_id),
                amount DECIMAL,
                status TEXT,
                purchased_at TIMESTAMP
            );
        """)

        # 2. Inserção em Massa (Fast Load)
        insert_leads = "INSERT INTO leads VALUES %s"
        psycopg2.extras.execute_values(cur, insert_leads, leads_data)

        insert_purchases = "INSERT INTO purchases VALUES %s"
        psycopg2.extras.execute_values(cur, insert_purchases, purchases_data)

        conn.commit()
        cur.close()
        conn.close()

        print(f"✨ Sucesso! {len(leads_data)} leads e {len(purchases_data)} compras criadas.")

    except Exception as e:
        print(f"❌ Falha no banco: {e}")


if __name__ == "__main__":
    generate_financial_data()

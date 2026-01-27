import pandas as pd
import psycopg2

DB_PARAMS = {
    "host": "localhost", "database": "dev_db",
    "user": "dev_user", "password": "cygnusX-1book2", "port": "5432"
}


def analyze_root_cause():
    conn = psycopg2.connect(**DB_PARAMS)

    # Query para analisar Status por Canal e Dispositivo
    query = """
        SELECT
            l.channel,
            l.device,
            p.status,
            COUNT(*) as volume,
            SUM(p.amount) as lost_revenue
        FROM leads l
        JOIN purchases p ON l.lead_id = p.lead_id
        WHERE p.status != 'approved'
        GROUP BY 1, 2, 3
        ORDER BY volume DESC
    """
    df = pd.read_sql(query, conn)
    conn.close()

    print("\n" + "=" * 50)
    print("🔍 INVESTIGAÇÃO DE CAUSA RAIZ: COMPRAS NÃO APROVADAS")
    print("=" * 50)

    # Pivot table para facilitar a leitura
    pivot = df.pivot_table(index=['channel'], columns='status', values='volume', aggfunc='sum', fill_value=0)
    print(pivot)

    print("\n💰 Receita total 'presa' em análise/rejeitada por canal:")
    revenue_loss = df.groupby('channel')['lost_revenue'].sum().sort_values(ascending=False)
    print(revenue_loss)


if __name__ == "__main__":
    analyze_root_cause()

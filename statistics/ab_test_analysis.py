import pandas as pd
import psycopg2
from statsmodels.stats.proportion import proportions_ztest
import warnings

# Silencia o aviso do pandas sobre o uso de conexão direta
warnings.filterwarnings('ignore', category=UserWarning)

DB_PARAMS = {
    "host": "localhost", "database": "dev_db",
    "user": "dev_user", "password": "cygnusX-1book2", "port": "5432"
}


def analyze_experiment():
    try:
        conn = psycopg2.connect(**DB_PARAMS)

        # CORREÇÃO: Usando l.lead_id para evitar ambiguidade
        query = """
            SELECT
                l.test_group,
                COUNT(l.lead_id) as n_leads,
                SUM(CASE WHEN p.status = 'approved' THEN 1 ELSE 0 END) as n_purchases
            FROM leads l
            LEFT JOIN purchases p ON l.lead_id = p.lead_id
            GROUP BY l.test_group
        """

        df = pd.read_sql(query, conn)
        conn.close()

        # Extraindo dados para o teste
        control = df[df['test_group'] == 'Control'].iloc[0]
        treatment = df[df['test_group'] == 'Treatment'].iloc[0]

        successes = [treatment['n_purchases'], control['n_purchases']]
        nobs = [treatment['n_leads'], control['n_leads']]

        # Executando o Teste Z de Proporção
        z_stat, p_value = proportions_ztest(successes, nobs)

        print("\n" + "=" * 50)
        print("📊 RESULTADOS DO TESTE A/B (EXPERIMENTAÇÃO)")
        print("=" * 50)
        print(f"Grupo CONTROL:   Leads: {control['n_leads']} | Vendas: {control['n_purchases']} | Conv: {control['n_purchases'] / control['n_leads']:.2%}")
        print(f"Grupo TREATMENT: Leads: {treatment['n_leads']} | Vendas: {treatment['n_purchases']} | Conv: {treatment['n_purchases'] / treatment['n_leads']:.2%}")
        print("-" * 50)
        print(f"P-Valor: {p_value:.4f}")

        # Interpretação técnica (Nível de confiança de 95%)
        if p_value < 0.05:
            print("✅ RESULTADO ESTATISTICAMENTE SIGNIFICANTE!")
            print("A mudança no produto gerou um impacto real na conversão.")
        else:
            print("❌ RESULTADO SEM SIGNIFICÂNCIA ESTATÍSTICA.")
            print("A diferença observada pode ser apenas flutuação natural dos dados.")
        print("=" * 50 + "\n")

    except Exception as e:
        print(f"❌ Erro na análise: {e}")


if __name__ == "__main__":
    analyze_experiment()

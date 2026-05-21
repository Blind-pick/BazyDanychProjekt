import subprocess
import re
import sys
import time
import os
from datetime import datetime

CONTAINER_NAME = "cinema_db"
DB_USER = "postgres"
DB_NAME = "kino"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')

# Definicja plików wyjściowych (raport wynikowy oraz logi diagnostyczne)
REPORT_FILE = os.path.join(SCRIPT_DIR, f"benchmark_report_{TIMESTAMP}.txt")
LOG_FILE = os.path.join(SCRIPT_DIR, f"benchmark_logs_{TIMESTAMP}.txt")

def save_to_report(text):
    with open(REPORT_FILE, "a", encoding="utf-8") as f:
        f.write(text + "\n")

def save_to_logs(text):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(text + "\n")

def run_cmd(cmd, check=True):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        error_msg = f"BŁĄD WYKONANIA: {cmd}\n{result.stderr}"
        save_to_logs(error_msg)
        print(" [BŁĄD] Wystąpił krytyczny błąd systemu. Szczegóły zapisano w pliku logów.")
        sys.exit(1)
    return result.stdout

def setup():
    viewing_path = os.path.join(SCRIPT_DIR, "viewing_test.sql")
    reservation_path = os.path.join(SCRIPT_DIR, "reservation_test.sql")
    hot_row_path = os.path.join(SCRIPT_DIR, "hot_row_test.sql")
    
    print(" -> Kopiowanie skryptów SQL do kontenera bazy danych...")
    run_cmd(f"docker cp {viewing_path} {CONTAINER_NAME}:/tmp/read.sql")
    run_cmd(f"docker cp {reservation_path} {CONTAINER_NAME}:/tmp/write.sql")
    run_cmd(f"docker cp {hot_row_path} {CONTAINER_NAME}:/tmp/hot_row.sql")

def reset_stats():
    sql = "SELECT pg_stat_statements_reset();"
    run_cmd(f'docker exec -i {CONTAINER_NAME} psql -U {DB_USER} -d {DB_NAME} -c "{sql}"')

def run_test(script, clients, threads, duration):
    print(f" -> Uruchomiono scenariusz: {script} (Klienci: {clients}, Wątki: {threads}, Czas: {duration}s)...")
    cmd = (
        f"docker exec -i {CONTAINER_NAME} pgbench -U {DB_USER} -d {DB_NAME} "
        f"-f /tmp/{script} -c {clients} -j {threads} -T {duration} -P 5 "
        f"--max-tries=100 --failures-detailed"
    )
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    # Przekierowanie wewnętrznych ostrzeżeń/błędów pgbench do osobnego pliku logów
    if result.stderr:
        save_to_logs(f"[{datetime.now().strftime('%H:%M:%S')}] OSTRZEŻENIE ({script}):\n{result.stderr.strip()}\n{'-'*40}\n")
        
    return result.stdout

def get_db_metrics():
    sql = """
    SELECT 
        round(mean_exec_time::numeric, 2) || ' ms' as avg_time,
        calls,
        regexp_replace(substring(query from 1 for 80), '\\s+', ' ', 'g') as query_clean
    FROM pg_stat_statements 
    WHERE query NOT LIKE '%pg_stat%' AND query NOT LIKE '%psql%'
    ORDER BY total_exec_time DESC 
    LIMIT 3;
    """
    cmd = f'docker exec -i {CONTAINER_NAME} psql -U {DB_USER} -d {DB_NAME} -A -F "|" -c "{sql}"'
    return run_cmd(cmd)

def build_report_frame(title, pgbench_out, db_out):
    report = []
    report.append("\n" + "="*80)
    report.append(f" RAPORT WYDAJNOŚCI: {title}")
    report.append("="*80)
    
    tps = re.search(r"tps = (\d+\.\d+)", pgbench_out)
    latency = re.search(r"latency average = (\d+\.\d+) ms", pgbench_out)
    failed = re.search(r"failed: (\d+)", pgbench_out)
    
    report.append(f" [*] Przepustowość (TPS):     {tps.group(1) if tps else 'N/A'} transakcji/s")
    report.append(f" [*] Średnie opóźnienie:      {latency.group(1) if latency else 'N/A'} ms")
    if failed and int(failed.group(1)) > 0:
        report.append(f" [!] Odrzucone transakcje:    {failed.group(1)} (Błędy/Konflikty - szczegóły w logach)")
    else:
        report.append(f" [*] Odrzucone transakcje:    0")

    report.append("\n [ TOP 3 NAJBARDZIEJ OBCIĄŻAJĄCE ZAPYTANIA (pg_stat_statements) ]")
    lines = db_out.strip().split("\n")
    if len(lines) > 1:
        report.append(f" {'Średni czas':<12} | {'Wywołania':<10} | {'Fragment Zapytania SQL'}")
        report.append("-" * 80)
        for line in lines[1:]:
            parts = line.split("|")
            if len(parts) == 3:
                report.append(f" {parts[0]:<12} | {parts[1]:<10} | {parts[2]}...")
    else:
        report.append(" Brak zarejestrowanych zapytań w statystykach systemowych.")
    report.append("="*80 + "\n")
    
    # Zapis sformatowanej ramki do pliku raportu głównego
    save_to_report("\n".join(report))

if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(" INICJALIZACJA AUTOMATYCZNYCH TESTÓW WYDAJNOŚCIOWYCH")
    print(f" Raport wynikowy:   {os.path.basename(REPORT_FILE)}")
    print(f" Logi diagnostyczne: {os.path.basename(LOG_FILE)}")
    print(f"{'='*60}\n")
    
    save_to_report("="*80)
    save_to_report(" GŁÓWNY RAPORT TESTÓW WYDAJNOŚCIOWYCH (BENCHMARK)")
    save_to_report(f" Data wygenerowania: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    save_to_report("="*80 + "\n")
    
    save_to_logs(f"=== LOGI DIAGNOSTYCZNE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
    
    setup()
    print()
    
    # Scenariusz 1: OLAP
    reset_stats()
    out_read = run_test("read.sql", clients=80, threads=4, duration=30)
    metrics_read = get_db_metrics()
    build_report_frame("Profil OLAP - Złożone Zapytania Analityczne (Read-Heavy)", out_read, metrics_read)
    print(" [OK] Test profilu OLAP zakończony sukcesem.")
    
    time.sleep(5)
    
    # Scenariusz 2: OLTP
    reset_stats()
    out_write = run_test("write.sql", clients=40, threads=4, duration=30)
    metrics_write = get_db_metrics()
    build_report_frame("Profil OLTP - Masowe Równoległe Zapisy (Write-Heavy)", out_write, metrics_write)
    print(" [OK] Test profilu OLTP zakończony sukcesem.")

    time.sleep(5)

    # Scenariusz 3: Lock Contention
    reset_stats()
    out_hot_row = run_test("hot_row.sql", clients=80, threads=4, duration=30)
    metrics_hot_row = get_db_metrics()
    build_report_frame("Test Współbieżności - Zjawisko Lock Contention (Hot Row UPDATE)", out_hot_row, metrics_hot_row)
    print(" [OK] Test współbieżności i blokad zakończony sukcesem.")
    
    print(f"\n{'='*60}")
    print(" PROCEDURA TESTOWA ZAKOŃCZONA POMYŚLNIE")
    print(f" Wyniki zbiorcze zapisano w: {os.path.basename(REPORT_FILE)}")
    print(f"{'='*60}\n")
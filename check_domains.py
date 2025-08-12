import pyodbc

# 데이터베이스 연결
conn = pyodbc.connect('Server=devhakdb;Database=SVCMON;Trusted_Connection=True;MultipleActiveResultSets=true;Encrypt=no;')
cursor = conn.cursor()

print("=== 데이터베이스에서 직접 조회 ===")
cursor.execute("""
    SELECT d.id, ng.name as network_group_name, d.domain, d.site_name, d.owner_name, 
           d.owner_contact, d.is_active, d.created_at
    FROM domains d 
    LEFT JOIN network_groups ng ON d.network_group_id = ng.id
    ORDER BY d.id
""")

domains = cursor.fetchall()
if domains:
    print(f"총 {len(domains)}개의 도메인이 등록되어 있습니다:")
    for domain in domains:
        print(f"ID: {domain[0]}, 망구분: {domain[1]}, 도메인: {domain[2]}, 사이트명: {domain[3]}")
        print(f"  담당자: {domain[4]}, 연락처: {domain[5]}, 활성: {domain[6]}, 생성일: {domain[7]}")
        print()
else:
    print("등록된 도메인이 없습니다.")

print("\n=== 망구분 정보 ===")
cursor.execute("SELECT id, name FROM network_groups ORDER BY id")
network_groups = cursor.fetchall()
for ng in network_groups:
    print(f"ID: {ng[0]}, 이름: {ng[1]}")

conn.close()

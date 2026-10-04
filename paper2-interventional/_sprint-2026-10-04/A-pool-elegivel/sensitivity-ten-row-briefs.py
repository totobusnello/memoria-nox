import sqlite3, json
c=sqlite3.connect("file:serv0903.db?mode=ro&immutable=1",uri=True)
out={}
for d in ["2026-08-26","2026-08-27","2026-08-28","2026-08-29"]:
    ref=d+" 23:59:59"
    pool=set(r[0] for r in c.execute("""SELECT id FROM chunks WHERE julianday(?) - julianday(COALESCE(source_date, created_at)) <= 30 AND (COALESCE(importance,0) >= 0.7 OR COALESCE(pain,0) >= 0.7) AND (source_file LIKE 'memory/entities/%' OR source_file LIKE 'memory/lessons.md')""",(ref,)))
    srv=set(r[0] for r in c.execute("""SELECT chunk_id FROM brief_log WHERE substr(served_at,1,10)=? AND brief_id IN (SELECT brief_id FROM brief_log WHERE substr(served_at,1,10)=? GROUP BY brief_id HAVING COUNT(*)=10)""",(d,d)))
    n10=c.execute("SELECT COUNT(*) FROM (SELECT brief_id FROM brief_log WHERE substr(served_at,1,10)=? GROUP BY brief_id HAVING COUNT(*)=10)",(d,)).fetchone()[0]
    hrs=c.execute("SELECT COUNT(DISTINCT substr(served_at,12,2)) FROM brief_log WHERE substr(served_at,1,10)=?",(d,)).fetchone()[0]
    out[d]={"pool":len(pool),"ten_row_briefs":n10,"pool_served_by_ten_row_briefs_only":len(pool&srv),"distinct_utc_hours_with_serves":hrs}
print(json.dumps(out,indent=1))

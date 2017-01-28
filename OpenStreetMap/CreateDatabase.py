import sqlite3
import pprint
import string
conn = sqlite3.connect("OSM.sqlite")
c = conn.cursor()
#c.executescript(open('data_wrangling_schema.sql','r').read())




QUERRY_NODE = "SELECT COUNT(*) FROM nodes"

QUERRY_WAY = "SELECT COUNT(*) FROM ways"

QUERRY_UNI_USER = """SELECT COUNT(DISTINCT(e.uid))
FROM (SELECT uid FROM nodes UNION ALL SELECT uid FROM ways) e"""

QUERRY_FREQ_USER = """SELECT e.user, COUNT(*) as num
FROM (SELECT user FROM nodes UNION ALL SELECT user FROM ways) e
GROUP BY e.user
ORDER BY num DESC
LIMIT 5"""

QUERRY_ONETIME_USER = """SELECT COUNT(*)
    FROM
    (SELECT e.user, COUNT(*) as num
     FROM (SELECT user FROM nodes UNION ALL SELECT user FROM ways) e
     GROUP BY e.user
     HAVING num=1) u"""

QUERRY_AMENITY = """SELECT value, COUNT(*) as num FROM nodes_tags
WHERE key = 'amenity'
GROUP BY value
ORDER BY num
DESC LIMIT 5"""

QUERRY_RELIGION = """SELECT nodes_tags.value, COUNT(*) as num
     FROM nodes_tags JOIN (SELECT DISTINCT(id) FROM nodes_tags WHERE value='place_of_worship') i
    ON nodes_tags.id=i.id
WHERE nodes_tags.key='religion'
GROUP BY nodes_tags.value
ORDER BY num DESC
LIMIT 3"""

QUERRY_CUISINE = """SELECT nodes_tags.value, COUNT(*) as num
FROM nodes_tags
    JOIN (SELECT DISTINCT(id) FROM nodes_tags WHERE value='restaurant') i
    ON nodes_tags.id=i.id
WHERE nodes_tags.key='cuisine'
GROUP BY nodes_tags.value
ORDER BY num DESC
LIMIT 10"""

QUERRY_KEY = """SELECT key, COUNT(*) as num FROM nodes_tags
GROUP BY key
ORDER BY num
DESC LIMIT 3"""

QUERRY_SOURCE = """SELECT lower(value), COUNT(*) as num FROM nodes_tags
WHERE lower(key) = 'source'
GROUP BY lower(value)
ORDER BY num
DESC LIMIT 3"""

QUERRYS = [QUERRY_NODE,\
           QUERRY_WAY, \
           QUERRY_UNI_USER,\
           QUERRY_FREQ_USER,\
           QUERRY_ONETIME_USER,\
           QUERRY_AMENITY, \
           QUERRY_RELIGION, \
           QUERRY_CUISINE,\
           QUERRY_KEY,\
           QUERRY_SOURCE]

for count, querry in enumerate(QUERRYS):
    c.execute(querry)
    data=c.fetchall()
    print (count+1)
    pprint.pprint(data)

conn.close()
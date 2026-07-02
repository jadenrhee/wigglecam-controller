# Tools

Freerouting jars are fetched, not versioned:

```bash
curl -L -o tools/freerouting-1.9.jar \
  https://github.com/freerouting/freerouting/releases/download/v1.9.0/freerouting-1.9.0.jar
```

v1.9.0 is the version the pipeline uses (v2.2.x crashed on this
board's DSN — deep recursion in PolylineTrace.combine).

#!/bin/zsh
for i in 1 2 3 4 5 6 7 8 9 10; do
  sz=$(stat -f%z "/Users/santiagosantafe/Downloads/SabanaHack/datos/raw/fresa_afzaal2021_datasetninja/strawberry-disease-detection-DatasetNinja.tar")
  echo "try $i size $sz"
  if [ "$sz" -ge 408606720 ]; then echo COMPLETE; exit 0; fi
  curl -sS -L -C - --max-filesize 2000000000 -o "/Users/santiagosantafe/Downloads/SabanaHack/datos/raw/fresa_afzaal2021_datasetninja/strawberry-disease-detection-DatasetNinja.tar" 'https://assets.supervisely.com/remote/eyJsaW5rIjogInMzOi8vc3VwZXJ2aXNlbHktZGF0YXNldHMvMjI2OV9TdHJhd2JlcnJ5IERpc2Vhc2UgRGV0ZWN0aW9uL3N0cmF3YmVycnktZGlzZWFzZS1kZXRlY3Rpb24tRGF0YXNldE5pbmphLnRhciIsICJzaWciOiAiZXgrZlBQYW1jc2QxOTdQTU1UeGlWcWdOS0psSTViWFZNWkMzeFdldG1rZz0ifQ==?response-content-disposition=attachment%3B%20filename%3D%22strawberry-disease-detection-DatasetNinja.tar%22'
  sleep 2
done

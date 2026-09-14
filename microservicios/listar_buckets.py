from influx import crear_cliente

with crear_cliente() as client:
    buckets = client.buckets_api().find_buckets()

    for bucket in buckets.buckets:
        print(bucket.name)

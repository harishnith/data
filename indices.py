def parse_indices(sheet):
    data = sheet.get("M2:R12")

    result = []
    time_val = ""

    for i, row in enumerate(data):
        if len(row) < 6:
            continue

        if i == 0:
            time_val = row[5]

        result.append({
            "index": row[0],
            "cmp": row[1],
            "change": row[2],
            "percent": row[3]
        })

    return {"time": time_val, "data": result}
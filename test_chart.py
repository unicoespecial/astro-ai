from datetime import datetime
from jyotishganit import calculate_birth_chart, get_birth_chart_json_string

chart = calculate_birth_chart(
    birth_date=datetime(2005, 7, 4, 9, 10, 0),
    latitude=26.44,
    longitude=80.33,
    timezone_offset=5.5,
    name="Yash"
)

print(get_birth_chart_json_string(chart))
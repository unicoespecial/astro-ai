from datetime import datetime
from jyotishganit import calculate_birth_chart

chart = calculate_birth_chart(
    birth_date=datetime(1996, 2, 4, 14, 45, 0),
    latitude=19.07, longitude=72.87,
    timezone_offset=5.5, name="Test")

h = chart.d1_chart.houses[0]
print(vars(h))
{% extends "base.html" %}

{% block content %}

<h2>DMA Dashboard</h2>

<table>
    <tr>
        <th>Stock</th>
        <th>20 DMA</th>
        <th>50 DMA</th>
        <th>100 DMA</th>
    </tr>

    <tr>
        <td>RELIANCE</td>
        <td class="green">Above</td>
        <td class="green">Above</td>
        <td class="red">Below</td>
    </tr>

</table>

{% endblock %}
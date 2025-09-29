# Product Trend Chart Component

A reusable Django template component for displaying production trends by product using Chart.js bar charts.

## File Location
```
templates/reports/partials/product_trend_chart.html
```

## Service Method
The chart uses data from `ProductionCalculationService.calculate_product_trend()` method.

## Usage

### Basic Usage
```html
{% include 'reports/partials/product_trend_chart.html' with product_trend=product_trend %}
```

### Advanced Usage with Custom Parameters
```html
{% include 'reports/partials/product_trend_chart.html' with 
    product_trend=product_trend 
    chart_id='myCustomChart' 
    chart_title='Monthly Production by Product'
    chart_height='h-80'
    show_legend=True 
%}
```

## Required Context Variables

### `product_trend`
Dictionary returned by `ProductionCalculationService.calculate_product_trend()` containing:
- `chart_data`: Chart.js formatted data with labels and datasets
- `products`: Dictionary of products and their production data
- `date_range`: List of dates covered
- `total_products`: Total number of different products

## Optional Context Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `chart_id` | `'productTrendChart'` | Unique ID for the canvas element |
| `chart_title` | `'Production Trend by Product'` | Title displayed above the chart |
| `chart_height` | `'h-64'` | Tailwind CSS height class for the chart container |
| `show_legend` | `True` | Whether to display the chart legend |

## Examples in Different Views

### 1. Weekly Summary (Already Implemented)
```python
# views.py
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    # ... other context ...
    
    if form.is_valid():
        start_date = form.cleaned_data['week_start_date']
        end_date = start_date + timedelta(days=6)
        production_line = form.cleaned_data['production_line']
        
        product_trend = ProductionCalculationService.calculate_product_trend(
            start_date, end_date, production_line
        )
        context['product_trend'] = product_trend
    
    return context
```

```html
<!-- template.html -->
{% include 'reports/partials/product_trend_chart.html' with 
    product_trend=product_trend 
    chart_id='weeklyProductTrend' 
    chart_title='Weekly Production by Product' 
%}
```

### 2. Monthly Report Example
```python
# views.py
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    
    # Get monthly data
    month_start = date.today().replace(day=1)
    month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    product_trend = ProductionCalculationService.calculate_product_trend(
        month_start, month_end
    )
    context['monthly_product_trend'] = product_trend
    
    return context
```

```html
<!-- monthly_report.html -->
{% include 'reports/partials/product_trend_chart.html' with 
    product_trend=monthly_product_trend 
    chart_id='monthlyProductTrend'
    chart_title='Monthly Production Trends'
    chart_height='h-96'
%}
```

### 3. Dashboard Widget Example
```python
# dashboard view
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    
    # Last 7 days trend
    end_date = date.today()
    start_date = end_date - timedelta(days=6)
    
    recent_product_trend = ProductionCalculationService.calculate_product_trend(
        start_date, end_date
    )
    context['recent_product_trend'] = recent_product_trend
    
    return context
```

```html
<!-- dashboard.html -->
<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
    <div class="lg:col-span-2">
        {% include 'reports/partials/product_trend_chart.html' with 
            product_trend=recent_product_trend 
            chart_id='dashboardProductTrend'
            chart_title='Recent Product Performance (7 Days)'
            chart_height='h-48'
        %}
    </div>
</div>
```

### 4. Production Line Specific Example
```python
# production line report
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    
    production_line = get_object_or_404(ProductionLine, pk=self.kwargs['line_id'])
    start_date = date.today() - timedelta(days=30)
    end_date = date.today()
    
    line_product_trend = ProductionCalculationService.calculate_product_trend(
        start_date, end_date, production_line
    )
    context['line_product_trend'] = line_product_trend
    context['production_line'] = production_line
    
    return context
```

```html
<!-- line_report.html -->
{% include 'reports/partials/product_trend_chart.html' with 
    product_trend=line_product_trend 
    chart_id='lineProductTrend'
    chart_title=production_line.name|add:' - Product Trends (30 Days)'
    show_legend=True
%}
```

## Chart Features

- **Bar Chart Display**: Uses stacked bar chart for clear product comparison
- **Value Labels**: Displays production values directly on each bar for quick reference
- **Interactive**: Hover tooltips with detailed information
- **Responsive**: Automatically adjusts to container size
- **Multi-product**: Supports multiple products with different colors
- **Accessible**: Proper color contrast and screen reader support
- **Customizable**: Easy to modify colors, styling, and behavior

## Dependencies

- Chart.js (included via CDN in the component)
- Tailwind CSS (for styling)

## Browser Support

- Modern browsers supporting ES6+
- Chart.js 3.x compatibility

## Notes

- The chart automatically handles missing data points (shows as 0)
- Colors are automatically assigned from a predefined palette
- Chart scales automatically based on data range
- No data state is handled gracefully with informative messaging

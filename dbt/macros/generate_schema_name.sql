{# Use the layer name as the schema, so analysts read marts.respondents rather than main_marts.respondents. #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {{ custom_schema_name | trim if custom_schema_name else target.schema }}
{%- endmacro %}

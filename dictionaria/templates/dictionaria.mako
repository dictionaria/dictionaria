<%inherit file="app.mako"/>

<%block name="brand">
    <a href="${request.resource_url(request.dataset)}" class="brand">Dictionaria</a>
</%block>

<%block name="title">(beta)</%block>

${next.body()}

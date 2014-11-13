<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "parameters" %>


<h2>${_('Semantic field')} ${ctx.name}</h2>

<%util:table items="${ctx.meanings}" args="item">\
    <%def name="head()">
        <th>ID</th><th>${_('Parameter')}</th><th>Representation</th>
    </%def>
    <td>${h.link(request, item, label=item.id)}</td>
    <td>${h.link(request, item)}</td>
    <td>${item.representation}</td>
</%util:table>

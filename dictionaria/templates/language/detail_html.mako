<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "languages" %>
<%block name="title">${_('Language')} ${ctx.name}</%block>

<h2>${_('Language')} ${ctx.name}</h2>

<h3>Dictionaries</h3>
<ul class="unstyled">
    % for d in ctx.dictionaries:
    <li>
        ${h.link(request, d)} by ${h.linked_contributors(request, d)}
    </li>
    % endfor
</ul>

<%def name="sidebar()">
    ${util.language_meta()}
</%def>

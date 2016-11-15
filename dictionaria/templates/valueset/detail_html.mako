<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "contributions" %>

<%def name="sidebar()">
    <%util:well title="Dictionary">
        ${h.link(request, ctx.contribution)} by ${h.linked_contributors(request, ctx.contribution)}
        ${h.button('cite', onclick=h.JSModal.show(ctx.contribution.name, request.resource_url(ctx.contribution, ext='md.html')))}
    </%util:well>
</%def>


<h2>Words in ${h.link(request, ctx.language)} for meaning "${h.link(request, ctx.parameter)}"</h2>

<ul>
% for i, value in enumerate(ctx.values):
        <li>${h.link(request, value.word)}: ${value.word.description}</li>
% endfor
</ul>

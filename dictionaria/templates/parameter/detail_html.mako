<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "parameters" %>
<%block name="title">${_('Parameter')} ${ctx.name}</%block>

<h2>
    ${_('Parameter')} "${ctx.name}"
    ${u.concepticon_link(request, ctx)}
</h2>

% if ctx.description:
<div class="alert alert-info">
    <button type="button" class="close" data-dismiss="alert">&times;</button>
    ${ctx.description}
</div>
% endif

% if map_ or request.map:
${(map_ or request.map).render()}
% endif

${request.get_datatable('values', h.models.Value, parameter=ctx).render()}

<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "units" %>


<h2>${_('Units')}</h2>

% if req.query_params.get('contribution') and not ctx.contribution:
<div class="warning">
<p>
<strong>Warning:</strong>
no such dictionary:
<em>${req.query_params.get('contribution')}</em>
</p>
</div>
% endif

<div>
    ${ctx.render()}
</div>

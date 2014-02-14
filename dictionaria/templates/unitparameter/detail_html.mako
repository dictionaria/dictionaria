<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "unitparameters" %>

<h2>${_('Unit Parameter')} ${ctx.name}</h2>

<div>
    ${request.get_datatable('unitvalues', h.models.UnitValue, unitparameter=ctx).render()}
</div>
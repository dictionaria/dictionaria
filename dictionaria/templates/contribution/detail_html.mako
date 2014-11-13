<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "contributions" %>


<h2>${ctx.name} ${h.cite_button(request, ctx)}</h2>

<div class="tabbable">
    <ul class="nav nav-tabs">
        <li class="active"><a href="#tab1" data-toggle="tab">Words</a></li>
        <li><a href="#tab2" data-toggle="tab">Meta</a></li>
    </ul>
    <div class="tab-content">
        <div id="tab1" class="tab-pane active">
            ${request.get_datatable('units', h.models.Value, contribution=ctx).render()}
        </div>
        <div id="tab2" class="tab-pane">
            ${util.files()}
            ${util.data()}
        </div>
    </div>
    <script>
$(document).ready(function() {
    if (location.hash !== '') {
        $('a[href="#' + location.hash.substr(2) + '"]').tab('show');
    }
    return $('a[data-toggle="tab"]').on('shown', function(e) {
        return location.hash = 't' + $(e.target).attr('href').substr(1);
    });
});
    </script>
</div>

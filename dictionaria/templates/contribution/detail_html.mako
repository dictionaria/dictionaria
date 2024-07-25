<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! from clldutils.misc import slug %>
<%! active_menu_item = "contributions" %>

${util.codes(ctx.language)}

<h2>${ctx.name} ${h.cite_button(request, ctx)}
% if ctx.series:
 ${f'<span class="series-{slug(ctx.series)}"><nobr>{ctx.series}</nobr></span>'|n}
% endif
</h2>

<p>by ${h.linked_contributors(request, ctx)}</p>

<div class="tabbable">
    <ul class="nav nav-tabs">
        <li class="active"><a href="#about" data-toggle="tab">Dictionary information</a></li>
        <li><a href="#words" data-toggle="tab">Words</a></li>
        % if ctx.jsondata.get('second_tab'):
            <li><a href="#words2" data-toggle="tab">Words extra</a></li>
        % endif
        % if ctx.examples:
        <li><a href="#examples" data-toggle="tab">Examples</a></li>
        % endif
        % if ctx.sources:
            <li><a href="#sources" data-toggle="tab">Sources</a></li>
        % endif
    </ul>
    <div class="tab-content">
        <div id="about" class="tab-pane active">
            <div class="span8">
                ${util.files()}
                ${util.data()}
                ${ctx.description or ''|n}
            </div>
            <div class="span4">
                <div class="well well-small">
                    ${ctx.toc or ''|n}
                </div>
            </div>
        </div>
        <div id="words" class="tab-pane">
            ${request.get_datatable('units', h.models.Value, contribution=ctx).render()}
        </div>
        % if ctx.jsondata.get('second_tab'):
            <div id="words2" class="tab-pane">
                ${request.get_datatable('units', h.models.Value, contribution=ctx, second_tab=True).render()}
            </div>
        % endif
        % if ctx.examples:
        <div id="examples" class="tab-pane">
            ${request.get_datatable('sentences', h.models.Sentence, dictionary=ctx).render()}
        </div>
        % endif
        % if ctx.sources:
            <div id="sources" class="tab-pane">
                ${request.get_datatable('sources', h.models.Source, dictionary=ctx).render()}
            </div>
        % endif
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

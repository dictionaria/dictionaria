<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "units" %>


<%def name="sidebar()">
    <%util:well title="Dictionary">
        ${h.link(request, ctx.dictionary)} by ${h.linked_contributors(request, ctx.dictionary)}
        ${h.button('cite', onclick=h.JSModal.show(ctx.dictionary.name, request.resource_url(ctx.dictionary, ext='md.html')))}
    </%util:well>
    % for file in ctx._files:
        % if file.mime_type.startswith('image'):
        <img src="${h.data_uri(request.file_ospath(file), file.mime_type)}" class="img-polaroid">
        % endif
    % endfor
</%def>


<h2>Word ${ctx.name}</h2>

<p>
    % for file in ctx._files:
        % if file.mime_type.startswith('audio'):
        <audio controls="controls">
            <source src="${request.file_url(file)}"/>
        </audio>
        % endif
    % endfor
</p>

<table class="table table-nonfluid">
    % if ctx.description:
    <tr>
        <td>meaning</td>
        <td>${ctx.description}</td>
    </tr>
    % endif
    % if ctx.counterparts:
        <tr>
            <td>comparison meanings</td>
            <td>
                <ul class="unstyled">
                % for c in ctx.counterparts:
                    <li>${h.link(request, c.valueset.parameter)}</li>
                % endfor
                </ul>
            </td>
        </tr>
    % endif
    % for value in ctx.unitvalues:
    <tr>
        <td>${h.link(request, value.unitparameter)}</td>
        <td>${value}</td>
    </tr>
    % endfor
% for _d in ctx.data:
    <tr>
        <td>${_d.key}</td>
        <td>${_d.value}</td>
    </tr>
% endfor
</table>

% if ctx.sentence_assocs:
<h4>Examples</h4>
${util.sentences(ctx)}
% endif

% if ctx.linked_from or ctx.links_to:
<h4>Related</h4>
<ul>
    % for w in set(list(ctx.linked_from) + list(ctx.links_to)):
        <li>${h.link(request, w)}</li>
    % endfor
</ul>
% endif

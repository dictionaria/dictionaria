<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "sentences" %>

<%block name="head">
    <script src="${request.static_url('clld:web/static/audiojs/audio.min.js')}"></script>
    <script>
        audiojs.events.ready(function() {
            var as = audiojs.createAll();
        });
    </script>
</%block>

<%def name="sidebar()">
    <%util:well title="Dictionary">
        <% dictionary = ctx.meaning_assocs[0].meaning.word.dictionary %>
        ${h.link(request, dictionary)} by ${h.linked_contributors(request, dictionary)}
        ${h.button('cite', onclick=h.JSModal.show(dictionary.name, request.resource_url(dictionary, ext='md.html')))}
    </%util:well>
</%def>

<h2>${_('Sentence')} ${ctx.id}</h2>
<dl>
    <dt>Language:</dt>
    <dd>${h.link(request, ctx.language)}</dd>
    <dt>Meanings:</dt>
    <dd>
        <ul>
            % for wa in ctx.meaning_assocs:
                <li>
                    ${h.link(request, wa.meaning.word, label=wa.meaning.name)}
                    [${wa.meaning.word.name}]
                </li>
            % endfor
        </ul>
    </dd>
</dl>

${h.rendered_sentence(ctx)|n}

% if getattr(ctx, 'audio'):
<div>
    <audio controls="controls">
        <source src="${request.file_url(ctx.audio)}"/>
    </audio>
</div>
% endif

<dl>
% if ctx.comment:
<dt>Comment:</dt>
<dd>${ctx.markup_comment or ctx.comment|n}</dd>
% endif
% if ctx.type:
<dt>${_('Type')}:</dt>
<dd>${ctx.type}</dd>
% endif
% if ctx.references or ctx.source:
<dt>${_('Source')}:</dt>
% if ctx.source:
<dd>${ctx.source}</dd>
% endif
% if ctx.references:
<dd>${h.linked_references(request, ctx)|n}</dd>
% endif
% endif
</dl>
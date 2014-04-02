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
<div class="well well-small">
<dl>
    <dt>Language:</dt>
    <dd>${h.link(request, ctx.language)}</dd>
    <dt>Words:</dt>
    <dd>
        <ul>
            % for wa in ctx.word_assocs:
            <li>${h.link(request, wa.word)} ${wa.description or ''}</li>
            % endfor
        </ul>
    </dd>
</dl>
</div>
</%def>

<h2>${_('Sentence')} ${ctx.id}</h2>

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
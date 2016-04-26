<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "units" %>

<%block name="head">
    <script src="${request.static_url('clld:web/static/audiojs/audio.min.js')}"></script>
    <script>
        audiojs.events.ready(function() {
            var as = audiojs.createAll();
        });
    </script>
</%block>

<%def name="sentences(obj=None, fmt='long')">
    <% obj = obj or ctx %>
    <ul id="sentences-${obj.pk}" class="unstyled">
        % for a in obj.sentence_assocs:
            <li>
                <blockquote style="margin-top: 5px;">
                ${h.link(request, a.sentence, label='%s %s:' % (_('Sentence'), a.sentence.id))}<br>
                % if a.description and fmt == 'long':
                    <p>${a.description}</p>
                % endif
                ${h.rendered_sentence(a.sentence, fmt=fmt)}
                % if a.sentence.alt_translation:
                <div>
                    <span class="translation">${a.sentence.alt_translation}</span>
                    <span>[${a.sentence.alt_translation_language}]</span>
                </div>
                % endif
            % if a.sentence.audio:
            <div>
                <audio src="${request.file_url(a.sentence.audio)}"/>
            </div>
            % endif
            % if a.sentence.references and fmt == 'long':
            <p>Source: ${h.linked_references(request, a.sentence)|n}</p>
            % endif
                    </blockquote>
            </li>
        % endfor
    </ul>
</%def>

<%def name="sidebar()">
    <%util:well title="Dictionary">
        ${h.link(request, ctx.dictionary)} by ${h.linked_contributors(request, ctx.dictionary)}
        ${h.button('cite', onclick=h.JSModal.show(ctx.dictionary.name, request.resource_url(ctx.dictionary, ext='md.html')))}
    </%util:well>
    % for file in ctx._files:
        % if file.mime_type.startswith('image'):
            <div class="img-with-caption">
                <img src="${h.data_uri(request.file_ospath(file), file.mime_type)}" class="img-polaroid">
                % if file.jsondata.get('copyright'):
                    <p>© ${file.jsondata.get('copyright')}</p>
                % endif
            </div>
        % endif
    % endfor
</%def>

<h2><span class="lemma">${ctx.name}</span></h2>

<p>
    % for file in ctx._files:
        % if file.mime_type.startswith('audio'):
        <audio src="${request.file_url(file)}"/>
        % endif
    % endfor
</p>

<table class="table table-nonfluid">
    % if ctx.pos:
    <tr>
        <td>Part of speech</td>
    <td>
        ${ctx.pos}
    </td>
    </tr>
    % endif
    % if ctx.counterparts:
        <tr>
            <td>comparison meanings</td>
            <td>
                <ul class="unstyled">
                % for c in ctx.counterparts:
                    <li>
                        ${h.link(request, c.valueset.parameter)}
                    </li>
                % endfor
                </ul>
            </td>
        </tr>
    % endif
    % for value in ctx.unitvalues:
    <tr>
        <td>${h.link(request, value.unitparameter)}</td>
        <td>
            ${value}
            % if value.name:
                (${value.name})
            % endif
        </td>
    </tr>
    % endfor
% for _d in ctx.data:
    % if not _d.key.startswith('lang-'):
    <tr>
        <td>${_d.key}</td>
        <td>${_d.value}</td>
    </tr>
    % endif
% endfor
</table>

<h4>Meanings</h4>
<ol>
    % for m in ctx.meanings:
        <li>
            % if m.language != 'en':
                ${m.language}:
            % endif
            <strong>${m.name}</strong>
            % if m.language == 'en':
                % if m.gloss and m.name != m.gloss:
                [${m.gloss}]
                % endif
                % if m.semantic_domain:
                    (${m.semantic_domain})
                % endif
                % if m.sentence_assocs:
                    ${sentences(m)}
                % endif
            % endif
        </li>
    % endfor
</ol>

% if ctx.linked_from or ctx.links_to:
<h4>Related</h4>
<ul>
    % for w, desc in set(list(ctx.linked_from) + list(ctx.links_to)):
        <li>
            <span class="lemma">${h.link(request, w)}</span>
            % if desc:
            <span>(${desc})</span>
            % endif
        </li>
    % endfor
</ul>
% endif

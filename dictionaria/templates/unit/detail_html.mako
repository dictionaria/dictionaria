<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "units" %>

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
                % if a.sentence.alt_translation1:
                <div>
                    ${a.sentence.dictionary.metalanguage_label(a.sentence.alt_translation_language1)|n}
                    <span class="translation">${a.sentence.alt_translation1}</span>
                </div>
                % endif
                    % if a.sentence.alt_translation2:
                        <div>
                            ${a.sentence.dictionary.metalanguage_label(a.sentence.alt_translation_language2)|n}
                            <span class="translation">${a.sentence.alt_translation2}</span>
                        </div>
                    % endif
            % if a.sentence.audio:
            <div>
                ${u.cdstar.audio(a.sentence.audio)}
            </div>
            % endif
            % if (a.sentence.references or a.sentence.source) and fmt == 'long':
            Source: ${h.linked_references(request, a.sentence)|n} <span class="label">${a.sentence.source}</span>
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
            <div class="img-with-caption well">
                ${u.cdstar.linked_image(file)}
                ##<img src="${h.data_uri(request.file_ospath(file), file.mime_type)}" class="img-polaroid">
                % if file.jsondata.get('copyright'):
                    <p>© ${file.jsondata.get('copyright')}</p>
                % endif
            </div>
        % endif
    % endfor
</%def>

<h2>${ctx.label}</h2>

<p>
    % for file in ctx._files:
        % if file.mime_type.startswith('audio'):
            ${u.cdstar.audio(file)}
        ##<audio src="${request.file_url(file)}"/>
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
            <ul class="unstyled">
                <li>
                    <strong>${m.name}</strong>
                    % if m.semantic_domain_list:
                        <ul class="inline semantic_domains_inline">
                            % for sd in m.semantic_domain_list:
                                <li><span class="label">${sd}</span></li>
                            % endfor
                        </ul>
                    % endif
                ##% if m.gloss and m.name != m.gloss:
                ##    [${m.gloss}]
                ##% endif
                % if m.reverse and m.reverse != m.name:
                    Comparison meaning: <strong>${m.reverse}</strong>
                % endif
                    </li>
            % if m.alt_translation1:
                <li>
                    ${ctx.dictionary.metalanguage_label(m.alt_translation_language1)|n}
                    <strong>${m.alt_translation1}</strong>
                </li>
            % endif
            % if m.alt_translation2:
                <li>
                    ${ctx.dictionary.metalanguage_label(m.alt_translation_language2)|n}
                    <strong>${m.alt_translation2}</strong>
                </li>
            % endif
                % if m.sentence_assocs:
                    <li>${sentences(m)}</li>
                % endif
            </ul>
        </li>
    % endfor
</ol>

% if ctx.linked_from or ctx.links_to:
<h4>Related</h4>
<ul>
    % for w, desc in set(list(ctx.linked_from) + list(ctx.links_to)):
        <li>
            % if desc:
                <span>${desc}:</span>
            % endif
            <span style="margin-right: 10px">${h.link(request, w, title=w.name, label=w.label)|n}</span>
            <strong>${'; '.join(w.description_list)}</strong>
        </li>
    % endfor
</ul>
% endif

<%! from itertools import chain %>

<%def name="sentences(obj=None, fmt='long')">
    <% obj = obj or ctx %>
    <ul id="sentences-${obj.pk}" class="unstyled">
        % for a in obj.sentence_assocs:
            <li>
                <blockquote style="margin-top: 5px;">
                    ${h.link(request, a.sentence, label='%s %s:' % (_('Sentence'), a.sentence.number))}<br>
                    % if a.description and fmt == 'long':
                        <p>${a.description}</p>
                    % endif
                    ${h.rendered_sentence(a.sentence, fmt=fmt)}
                    % if a.sentence.alt_translation1:
                        <div class="alt_translation">
                            <span class="alt-translation translation">${a.sentence.alt_translation1}</span>
                            <span class="alt-translation">[${a.sentence.alt_translation_language1}]</span>
                        </div>
                    % endif
                    % if a.sentence.alt_translation2:
                        <div class="alt_translation">
                            <span class="alt-translation translation">${a.sentence.alt_translation2}</span>
                            <span class="alt-translation">[${a.sentence.alt_translation_language2}]</span>
                        </div>
                    % endif
                    % if a.sentence.audio:
                        <div>
                            ${u.cdstar.audio(a.sentence.audio)}
                        </div>
                    % endif
                    % if (a.sentence.references or a.sentence.source) and fmt == 'long':
                        Source: ${h.linked_references(request, a.sentence)|n} <span class="muted">${a.sentence.source}</span>
                    % endif
                </blockquote>
            </li>
        % endfor
    </ul>
</%def>

<%def name="word_details()">
    <table class="table table-condensed table-nonfluid borderless">
        % if ctx.pos:
            <tr>
                <td><small>part of speech</small></td>
                <td>
                    <span class="vocabulary">${ctx.pos}</span>
                    % if links and 'pos' in links:
                        <small>${links['pos']|n}</small>
                    % endif
                </td>
            </tr>
        % endif
        % if [m for m in ctx.meanings if m.reverse]:
            <tr>
                <td><small>comparison meanings</small></td>
                <td>
                    <ul class="unstyled">
                        % for m in ctx.meanings:
                            % for re in m.reverse_list:
                                % if re not in [c.valueset.parameter.name for c in ctx.counterparts]:
                                    <li>${re}</li>
                                % endif
                            % endfor
                        % endfor
                    </ul>
                </td>
            </tr>
        % endif
        % for value in ctx.unitvalues:
            <tr>
                <td>${h.link(request, value.unitparameter)}</td>
                <td>
                    <small>
                        ${value}
                        % if value.name:
                            (${value.name})
                        % endif
                    </small>
                </td>
            </tr>
        % endfor
        % for _d in ctx.data:
            % if not _d.key.startswith('lang-') and not _d.key.endswith('_links'):
                <tr>
                    <td><small>${_d.key}</small></td>
                    <td>
                        ${_d.value}
                        % if links and _d.key in links:
                            <small>${links[_d.key]|n}</small>
                        % endif
                    </td>
                </tr>
            % endif
        % endfor
    </table>

    ${'<ul class="unstyled">' if len(ctx.meanings) <= 1 else '<ol>'|n}
        % if links and 'de' in links:
            <li>
                <small>${links['de']|n}</small>
            </li>
        % endif
    % for m in ctx.meanings:
        <li>
            <ul class="unstyled">
                <li>
                    <strong>${m.name}</strong>
                    ##% if m.gloss and m.name != m.gloss:
                ##    [${m.gloss}]
                ##% endif
                    </li>
                % if m.alt_translation1:
                    <li>
                        <span class="alt-translation">${m.alt_translation1} [${m.alt_translation_language1}]</span>
                    </li>
                % endif
                % if m.alt_translation2:
                    <li>
                        <span class="alt-translation">${m.alt_translation2} [${m.alt_translation_language2}]</span>
                    </li>
                % endif
                % if m.semantic_domain_list:
                    <li>
                        <ul class="inline semantic_domains_inline">
                            % for sd in m.semantic_domain_list:
                                <li><span class="vocabulary">${sd}</span></li>
                            % endfor
                        </ul>
                    </li>
                % endif
                % if m.sentence_assocs:
                    <li>${sentences(m)}</li>
                % endif
            </ul>
        </li>
    % endfor
    ${'</ul>' if len(ctx.meanings) <= 1 else '</ol>'|n}

    <% rels = list(chain(ctx.links_to)) or list(chain(ctx.linked_from)) %>
    % if rels:
        <h4>Related entries</h4>
        <ul>
            % for desc, words in rels:
                <li>
                    % if desc:
                        <span>${desc}:</span>
                    % endif
                    <ul class="inline">
                        % for w in words:
                            <li>
                                <span style="margin-right: 10px">${h.link(request, w, title=w.name, label=w.label)|n}</span>
                                <strong>${'; '.join(w.description_list)}</strong>
                            </li>
                        % endfor
                    </ul>
                </li>
            % endfor
        </ul>
    % endif
</%def>

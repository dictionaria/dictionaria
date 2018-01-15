<%inherit file="dictionaria.mako"/>
<%namespace name="util" file="util.mako"/>
<%! active_menu_item = "help" %>


<h2 id="Structure of entries and basic features">Structure of entries and basic
    features</h2>

<h2 id="How to search...">How to search...</h2>

<p>Dictionaria facilitates two kinds of searches:</p>

<ol>
    <li>For the searches of headwords, meaning descriptions, and examples you type the
        word or multiwor
        d expression into the search field, e.g. pull or pull out. The unmarked search
        finds the item, but
        in addition all other items that contain the same string of characters. Thus eat
        does not only find
        'eat', but also 'beat' and 'creature'.
        To narrow your searches by the use of the symbols listed in Table 1, in which x
        means any character
        or string of characters including space.

        <table class="table table-bordered">
            <caption>Table 1: Search options</caption>
            <tbody>
            <tr>
                <td>^x</td>
                <td>search for a certain word or string of characters at the beginning of
                    an entry, e.g. "^under",
                    which finds <em>under, underground, understand</em> etc.
                </td>
            </tr>
            <tr>
                <td>x$</td>
                <td>search for a certain word or string of characters at the end of an
                    entry, e.g. "fly$", which fi
                    nds <em>fly, butterfly,</em> etc.
                </td>
            </tr>
            <tr>
                <td>x_x</td>
                <td>search for entries showing the string preceded and followed by any
                    other character including wh
                    ite space, e.g. "_ea_" finds beach, tea leaf, burn / eat
                </td>
            </tr>
            <tr>
                <td>^x$</td>
                <td>search for a string of characters that fills the headword or meaning
                    description from the begin
                    ning to the end. "^eat$" finds "eat" in the meaning description of the
                    Daakaka dictionary, because
                    this consists only of "eat", but it does not find "eat" in the Teop
                    meaning description, because th
                    is is "eat (something with something)"
                </td>
            </tr>
            </tbody>
        </table>
    </li>
    <li>For searches of parts of speech and semantic domains the dictionaries provide
        individual drop-d
        own lists.
    </li>
</ol>

<h3 id="...single dictionaries">...single dictionaries</h3>

<h4 id="...single columns">...single columns</h4>

<br>
<table class="table table-bordered">
    <caption>Table 2: Single column searches</caption>
    <tbody>
    <tr>
        <td>Headword</td>
        <td>
            <p>If you type a word into the ‘headword’ field, you will find this word
                listed together wi
                th all other words that contain the same string of characters.</p>
            <p>For example, 'ep' (Daakaka) finds not only the headword 'ep', but also <em>akr<strong>ep
            </strong></em>, <em>b<strong>ep</strong>ane</em> and <em>dokta ane
                <strong>ep</strong></em>.</p>
            <br>
            <p>You can narrow down your search by using the search option '^' directly
                followed by the
                word you are looking for. This search will find the headword (if it is
                present in the dictionary) a
                nd all other headword entries that begin with the characters of this
                headword.</p>
            <p>For example, if you search for '^ep', you will see the following entries:
                <em><strong>ep
                    ¹, ep², ep</strong>mir, <strong>ep</strong>upuop</em>.</p>
            <br>
            <p>If you want to find all headwords ending in a particular string of
                characters, type the
                string into the headword field and directly add '$' at the end of the
                string.</p>
            <p>For example, if you search for 'ep$' you will find
                <em>akr<strong>ep</strong>, dewen<strong>ep</strong></em> and <em>tuwu
                    tr<strong>ep</strong></em>.</p>
            <br>
            <p>If you combine '^' and '$' as in '^ep$', you find <em>ep¹</em> and
                <em>ep²</em>.</p>
        </td>
    </tr>
    <tr>
        <td>Meaning description</td>
        <td>
            <p>If you type in a particular English word in the field 'meaning
                description', you will fi
                nd all meaning descriptions that contain this string of characters at any
                position.</p>
            <p>For example, a search for 'man' will give you the entry for 'man' but also
                'praying <strong>man</strong>tis' and 'hu<strong>man</strong> tongue'
                (Daakaka).</p>
            <br>
            <p>You can use the search option '^' directly followed by the word you are
                looking for. Thi
                s will give you all meaning descriptions that start with the searched
                word.</p>
            <p>For example, if you search for ‘^man’, you will find the entry
                '<strong>man</strong>; pe
                rson' but also '<strong>man</strong>go'.</p>
            <br>
            <p>If you type in '^man$, you will get no results, because '$' means 'end of
                entry' and the
                meaning descriptions are 'man; guy' for <em>teme</em> and 'man; person'
                for <em>vyante</em>.</p>
        </td>
    </tr>
    <tr>
        <td>Part of speech</td>
        <td>The drop-down list shows all word classes and in some dictionaries classes of
            affixes and types
            of multi-word constructions. The abbreviations are listed in the respective
            introduction of the dictionary.
        </td>
    </tr>
    <tr>
        <td>Semantic domain</td>
        <td>The drop-down list shows a selection of semantic domains covered by the
            dictionary, for example
            'plants' in the Daakaka and the Teop dictionary or 'botanical' in the Hdi
            dictionary.
        </td>
    </tr>
</table>

<h4 id="...across columns">...across columns</h4>

<ol>
    <li>Part of speech & meaning description
        <br>
        <p>For example, if you select 'v.tr' in 'part of speech' and enter 'hand' in
            'meaning description'
            in the Teop dictionary, you find:</p>
        <br>
        <p><em>atoato</em> 'catch something with one's <strong>hand</strong>s'</p>
        <p><em>kae</em> 'hold something in one <strong>hand</strong>'</p>
        <p><em>poto</em> 'grab something or catch something with one's
            <strong>hand</strong>
            s'</p>
        <br>
        <p>In the Daakaka dictionary the search for 'v.tr' and 'hand' finds:</p>
        <br>
        <p><em>bwiti</em> 'break an elongated object in two with both
            <strong>hand</strong>s'
        </p>
        <p><em>kinkate</em> 'hold something in one <strong>hand</strong>'</p>
        <p><em>sedisi</em> 'raise a weapon (in one <strong>hand</strong>) to hit someone
        </p>
        <p><em>tiwiye</em> 'break (something which can be broken easily with two <strong>hand</strong>s)
        </p>
    </li>

    <li>Part of speech and semantic domain
        <br>
        <p>For example, if you select 'v.itr' and 'body' you find 7 entries in the Daakaka
            dictionary, e.g.
        </p>
        <br>
        <p><em>banga</em> 'open one's mouth'</p>
        <p><em>kyep</em> 'shit'</p>
        <br>
        <p>In the Teop dictionary the selection of 'v.intr' and 'body' finds 8 entried,
            e.g.</p>
        <br>
        <p><em>goroho</em> 'sleep'</p>
        <p><em>kayuhu</em> 'spit'</p>

    </li>
</ol>

<h3 id="...across dictionaries">...across dictionaries</h3>

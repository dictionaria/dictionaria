<%inherit file="dictionaria.mako"/>
<%namespace name="util" file="util.mako"/>
<%! active_menu_item = "help" %>

<h2 id="Using the Dictionaria search fields">Using the Dictionaria search fields</h2>

<h3 id="Single column searches">Single column searches</h3>

<p>In the search fields above the different columns of the “Words (extra)” tab you can search for any sequence of characters. A character is a letter, digit, symbol, or a single blank space. Here are some examples of the different kinds of search strategies that can be employed:</p>

<br>
<table class="table table-bordered">
<thead>
	<tr>
	<td colspan="3">If you type into the search field:</td>
	<td>you can find, for example, the words or descriptions of this kind:</td>
	<td>The characters typed into the search field will match:</td>
	</tr>
</thead>
<tbody>
	<tr>
	<td colspan="3"><b>eat</b></td>
	<td><em>b<b>eat</b>; br<b>eat</b>h; <b>eat</b>; w<b>eat</b>her; …</em></td>
	<td>all entries with words containing  the character sequence <em>eat</em></td>
	</tr>
	<tr>
	<td colspan="3"><b>^eat<b></td>
	<td><em><b>eat</b>; <b>eat</b>er; <b>eat</b>ing; <b>Eat</b>on; …</em></td>
	<td>all entries with the character sequence <em>eat</em> at the <b>beginning</b> of the field</td>
	</tr>
	<tr>
	<td colspan="2"><b>^eat</b></td>
	<td>SPACE</td>
	<td><em><b>eat</b> an apple; <b>eat</b> meat; …</em></td>
	<td>all entries with the word <em>eat</em> at the beginning of the field followed by a space and more material</td>
	</tr>
	<tr>
	<td>SPACE</td>
	<td><b>eat</b></td>
	<td>SPACE</td>
	<td><em>dog <b>eat</b> dog; all plants which <b>eat</b> insects; …</em></td>
	<td>all entries with the word <em>eat</em> within the entry field</td>
	</tr>
	<tr>
	<td colspan="3"><b>eat$</b></td>
	<td><em>heartb<b>eat</b>; <b>eat</b>; m<b>eat</b>; tr<b>eat</b>; …</em></td>
	<td>all entries with the character sequence <em>eat</em> at the end of the field</td>
	</tr>
	<tr>
	<td colspan="2">SPACE</td>
	<td><b>eat$</b></td>
	<td><em>a bite to <b>eat</b>; fit to <b>eat</b>; …</em></td>
	<td>all entries with the word <em>eat</em> at the end of the field</td>
	</tr>
	<tr>
	<td colspan="3"><b>^eat$</b></td>
	<td><em>eat</em></td>
	<td>all entries containing exactly the character sequence <em>eat</em> in the entry field and nothing else</td>
	</tr>
	<tr>
	<td colspan="3"><b>eat%eat</b></td>
	<td><em>br<b>eat</b>he heavily; be out of br<b>eat</b>h</em></td>
	<td>all entries containing the sequences entered in the exact order</td>
	</tr>
	<tr>
	<td colspan="3"><b>_eat</b></td>
	<td><em><p>m<b>eat</b></p>
            <p>fish and other cr<b>eat</b>ures that swim</p></em></td>
	<td>all entries containing the sequence <em>eat</em>, but <em>not at the beginning of the entry</em></td>
	</tr>
	<tr>
	<td colspan="3"><b>eat_</b></td>
	<td><em><p>cr<b>eat</b>ure; animal</p>
            <p>bad w<b>eat</b>her</p></em></td>
	<td>all entries containing the sequence <em>eat</em>, but <em>not at the end of the entr</em>y</td>
	</tr>
	<tr>
	<td colspan="3"><b>_eat_</b></td>
	<td><em>attach a f<b>eat</b>her to something</em></td>
	<td>all entries containing the sequence <em>eat</em>, but <em>not at the beginning or end of the entry</em> (only in the middle)</td>
	</tr>
</tbody>
</table>

<p>For searching the fields 'Part of speech' and 'Semantic domain' you can choose categories from the drop-down lists:</p>

<br>
<table class="table table-bordered">
<tr>
<td>Part of speech</td>
<td>The drop-down list shows all word classes and in some dictionaries classes of affixes and types of multi-word constructions. The abbreviations are listed in the respective introduction of the dictionary.</p>
</tr>
<tr>
<td>Semantic domain</td>
<td>The drop-down list shows a selection of semantic domains covered by the dictionary, for example 'plants' in the Daakaka and the Teop dictionary or 'botanical' in the Hdi dictionary.</td>
</tr>
<tr>
<td>Examples</td>
<td>Typing in a number will filter for entries with the same exact number of examples. Using the more than/less then/equal sign will give a range. For example: “>1” will give entries that have more than one examples. “=>1” will give entries with one example or more.</td>
</tr>
</table>

<h3 id="Search across columns">Search across columns</h3>

<ol>
<li>Part of speech & meaning description
<br>
<p>For example, if you select 'vt' in 'part of speech' and enter 'hand' in 'meaning description' in the Teop dictionary, you will find:</p>
<br>
    <ul>
        <li><em>atoato</em>:		'catch something with one's <strong>hand</strong>s'</li>
        <li><em>kae</em>:			'hold something in one <strong>hand</strong>'</li>
        <li><p><em>poto</em>:		'grab something or catch something with one's <strong>hand</strong>s'</li>
    </ul>
<br>
<p>In the Daakaka dictionary the search for 'v.tr' and 'hand' finds:</p>
<br>
    <ul>
        <li><em>bwiti</em>:		'break an elongated object in two with both <strong>hand</strong>s'</li>
        <li><em>kinkate</em>:		'hold something in one <strong>hand</strong>'</li>
        <li><em>sedisi</em>:		'raise a weapon (in one <strong>hand</strong>) to hit someone</li>
        <li><em>tiwiye</em>:		'break (something which can be broken easily with two <strong>hand</strong>s)</li>
    </ul>
</li>
<br>
<li>Part of speech and semantic domain
<br>
<p>For example, if you select 'v.itr' and 'body' you find 7 entries in the Daakaka dictionary, e.g.</p>
<br>
    <ul>
        <li><em>banga</em>:		'open one's mouth'</li>
        <li><em>kyep</em>:		'shit'</li>
    </ul>
<br>
<p>In the Teop dictionary the selection of 'vi' and 'body' finds 8 entried, e.g.</p>
<br>
    <ul>
        <li><em>goroho</em>:		'sleep'</li>
        <li><em>kayuhu</em>:		'spit'</li>
    </ul>
</li>
</ol>

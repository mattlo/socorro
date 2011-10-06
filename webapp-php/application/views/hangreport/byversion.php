<?php slot::start('head') ?>
    <title>Hang Report for <?php out::H($product) ?> <?php out::H($version) ?></title>
    <?php echo html::script(array(
       'js/jquery/plugins/ui/jquery.tablesorter.min.js',
       'js/jquery/plugins/jquery.girdle.min.js',
       'js/socorro/hangreport.js',
    ))?>
    <?php echo html::stylesheet(array(
        'css/flora/flora.tablesorter.css'
    ), 'screen')?>

<?php slot::end() ?>

<div class="page-heading">
  <h2>Hang Report for <span class="current-product"><?php out::H($product) ?></span> <span class="current-version"><?php out::H($version) ?></span></h2>
    <ul class="options">
        <li><a href="<?php echo url::base(); ?>hangreport/byversion/<?php echo $product ?>/<?php echo $version ?>" class="selected">By Product/Version</a></li>
    </ul>
</div>


<div class="panel">
  <div class="body notitle">
    <table id="signatureList" class="tablesorter">
      <thead>
        <tr>
          <th class="header">Browser Signature</th>
          <th class="header">Plugin Signature</th>
          <th class="header">Flash Version</th>
<?php
// TODO only show if user authenticated
if (false) {
?>
          <th class="header">URL</th>
<?php
}
?>
          <th class="header">OOID</th>
          <th class="header">Duplicates</th>
          <th class="header">Report Day</th>
        </tr>
      </thead>
      <tbody>
<?php
if ($resp) {
    foreach ($resp->hangReport as $entry) {
    $sigParams = array(
        'date'        => $end_date,
        'signature'   => $entry->browser_signature
    );
    if (property_exists($entry, 'branch')) {
        $sigParams['branch'] = $entry->branch;
    } else {
        $sigParams['version'] = $product . ':' . $version;
    }

    $browser_link_url =  url::base() . 'report/list?' . html::query_string($sigParams);
    $sigParams['signature'] = $entry->plugin_signature;
    $plugin_link_url =  url::base() . 'report/list?' . html::query_string($sigParams);
    $uuid_link_url = url::base() . 'report/index/' . $entry->uuid;
?>
        <tr>
          <td>
            <a href="<?php out::H($browser_link_url) ?>" class="signature signature-preview"><?php out::H($entry->browser_signature) ?></a>
          </td>
          <td>
            <a href="<?php out::H($plugin_link_url) ?>" class="signature signature-preview"><?php out::H($entry->plugin_signature) ?></a>
          </td>
          <td>
            <?php out::H($entry->flash_version) ?>
          </td>
<?php
        // TODO only show if user authenticated
        if (false) {
?>
          <td>
            <?php out::H($entry->url) ?>
          </td>
<?php
        }
?>
          <td>
            <a href="<?php out::H($uuid_link_url)?>"><?php out::H($entry->uuid) ?></a>
          </td>
          <td>
<?php 
foreach ($entry->duplicates as $dup) {
?>
            <?php out::H($dup) ?>
<?php
        }
?>
          </td>
          <td>
            <?php out::H($entry->report_day) ?>
          </td>
        </tr>
<?php
    }
} else {
    View::factory('common/data_access_error')->render(TRUE);
}
?>
      <tbody>
    </table>
  </div>
</div>

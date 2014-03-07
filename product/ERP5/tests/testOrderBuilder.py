# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2008 Nexedi SA and Contributors. All Rights Reserved.
#          Łukasz Nowak <lukasz.nowak@ventis.com.pl>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
##############################################################################

import unittest

from Products.ERP5Type.tests.ERP5TypeTestCase import ERP5TypeTestCase
from DateTime import DateTime
from Products.ERP5Type.tests.Sequence import SequenceList
from Products.ERP5.tests.testOrder import TestOrderMixin
from Products.ERP5.tests.utils import newSimulationExpectedFailure

class TestOrderBuilderMixin(TestOrderMixin):

  run_all_test = 1

  order_builder_portal_type = 'Order Builder'

  order_module = 'purchase_order_module'
  order_portal_type = 'Purchase Order'
  order_line_portal_type = 'Purchase Order Line'
  order_cell_portal_type = 'Purchase Order Cell'

  packing_list_portal_type = 'Internal Packing List'
  packing_list_line_portal_type = 'Internal Packing List Line'
  packing_list_cell_portal_type = 'Internal Packing List Cell'

  # hardcoded values
  order_builder_hardcoded_time_diff = 10.0

  # defaults
  decrease_quantity = 1.0
  max_delay = 4.0
  min_flow = 7.0

  def afterSetUp(self):
    """
    Make sure to not use special apparel setting from TestOrderMixin
    """
    self.createCategories()

  def stepSetMaxDelayOnResource(self, sequence):
    """
    Sets max_delay on resource
    """
    resource = sequence.get('resource')
    resource.edit(max_delay=self.max_delay)

  def stepSetMinFlowOnResource(self, sequence):
    """
    Sets min_flow on resource
    """
    resource = sequence.get('resource')
    resource.edit(min_flow=self.min_flow)

  def stepFillOrderBuilder(self, sequence):
    """
    Fills Order Builder with proper quantites
    """
    order_builder = sequence.get('order_builder')
    organisation = sequence.get('organisation')
    resource = sequence.get('resource')

    order_builder.edit(
      delivery_module = self.order_module,
      delivery_portal_type = self.order_portal_type,
      delivery_line_portal_type = self.order_line_portal_type,
      delivery_cell_portal_type = self.order_cell_portal_type,
      destination_value = organisation,
      resource_portal_type = self.resource_portal_type,
      simulation_select_method_id='generateMovementListForStockOptimisation',
    )
    order_builder.newContent(
      portal_type = 'Category Movement Group',
      collect_order_group='delivery',
      tested_property=['source', 'destination',
                       'source_section', 'destination_section'],
      int_index=1
      )
    order_builder.newContent(
      portal_type = 'Property Movement Group',
      collect_order_group='delivery',
      tested_property=['start_date', 'stop_date'],
      int_index=2
      )

    order_builder.newContent(
      portal_type = 'Category Movement Group',
      collect_order_group='line',
      tested_property=['resource'],
      int_index=1
      )
    order_builder.newContent(
      portal_type = 'Base Variant Movement Group',
      collect_order_group='line',
      int_index=2
      )

    order_builder.newContent(
      portal_type = 'Variant Movement Group',
      collect_order_group='cell',
      int_index=1
      )

  def stepCheckGeneratedDocumentListVariated(self, sequence):
    """
    Checks documents generated by Order Builders with its properties for variated resource
    """
    organisation = sequence.get('organisation')
    resource = sequence.get('resource')

    # XXX: add support for more generated documents
    order, = sequence.get('generated_document_list')
    self.assertEqual(order.getDestinationValue(), organisation)
    self.assertEqual(order.getStartDate(), self.wanted_start_date)
    self.assertEqual(order.getStopDate(), self.wanted_stop_date)

    # XXX: ... and for more lines/cells too
    order_line, = order.contentValues(portal_type=self.order_line_portal_type)
    self.assertEqual(order_line.getResourceValue(), resource)
    self.assertEqual(order_line.getTotalQuantity(),
      sum(self.wanted_quantity_matrix.itervalues()))

    quantity_matrix = {}
    for cell in order_line.contentValues(portal_type=self.order_cell_portal_type):
      key = cell.getProperty('membership_criterion_category')
      self.assertFalse(key in quantity_matrix)
      quantity_matrix[key] = cell.getQuantity()
    self.assertEqual(quantity_matrix, self.wanted_quantity_matrix)

  def stepCheckGeneratedDocumentList(self, sequence):
    """
    Checks documents generated by Order Builders with its properties
    """
    organisation = sequence.get('organisation')
    resource = sequence.get('resource')

    # XXX: add support for more generated documents
    order, = sequence.get('generated_document_list')
    self.assertEqual(order.getDestinationValue(), organisation)
    self.assertEqual(order.getStartDate(), self.wanted_start_date)
    self.assertEqual(order.getStopDate(), self.wanted_stop_date)

    # XXX: ... and for more lines/cells too
    order_line, = order.contentValues(portal_type=self.order_line_portal_type)
    self.assertEqual(order_line.getResourceValue(), resource)
    self.assertEqual(order_line.getTotalQuantity(), self.min_flow)

  def stepBuildOrderBuilder(self, sequence):
    """
    Invokes build method for Order Builder
    """
    order_builder = sequence.get('order_builder')
    generated_document_list = order_builder.build()
    sequence.set('generated_document_list', generated_document_list)

  def stepCreateOrderBuilder(self, sequence):
    """
    Creates empty Order Builder
    """
    order_builder = self.portal.portal_orders.newContent(
      portal_type=self.order_builder_portal_type)
    sequence.set('order_builder', order_builder)

  def stepDecreaseOrganisationResourceQuantityVariated(self, sequence):
    """
    Creates movement with variation from organisation to None.
    Using Internal Packing List, confirms it.

    Note: Maybe use InventoryAPITestCase::_makeMovement instead of IPL ?
    """
    organisation = sequence.get('organisation')
    resource = sequence.get('resource')

    packing_list_module = self.portal.getDefaultModule(
      portal_type = self.packing_list_portal_type
    )

    packing_list = packing_list_module.newContent(
      portal_type = self.packing_list_portal_type,
      source_value = organisation,
      start_date = self.datetime,
      specialise = self.business_process,
    )

    packing_list_line = packing_list.newContent(
      portal_type = self.packing_list_line_portal_type,
      resource_value = resource,
      quantity = self.decrease_quantity,
    )

    packing_list_line.setVariationCategoryList(
      self.decrease_quantity_matrix.keys(),
    )

    self.tic()

    base_id = 'movement'
    cell_key_list = list(packing_list_line.getCellKeyList(base_id=base_id))
    cell_key_list.sort()

    for cell_key in cell_key_list:
      cell = packing_list_line.newCell(base_id=base_id,
                                portal_type=self.packing_list_cell_portal_type, *cell_key)
      cell.edit(mapped_value_property_list=['price','quantity'],
                quantity=self.decrease_quantity_matrix[cell_key[0]],
                predicate_category_list=cell_key,
                variation_category_list=cell_key)

    packing_list.confirm()

  def stepDecreaseOrganisationResourceQuantity(self, sequence):
    """
    Creates movement from organisation to None.
    Using Internal Packing List, confirms it.

    Note: Maybe use InventoryAPITestCase::_makeMovement instead of IPL ?
    """
    organisation = sequence.get('organisation')
    resource = sequence.get('resource')

    packing_list_module = self.portal.getDefaultModule(
      portal_type = self.packing_list_portal_type
    )

    packing_list = packing_list_module.newContent(
      portal_type = self.packing_list_portal_type,
      source_value = organisation,
      start_date = self.datetime+14,
      specialise = self.business_process,
    )

    packing_list.newContent(
      portal_type = self.packing_list_line_portal_type,
      resource_value = resource,
      quantity = self.decrease_quantity,
    )

    packing_list.confirm()

class TestOrderBuilder(TestOrderBuilderMixin, ERP5TypeTestCase):
  """
    Test Order Builder functionality
  """
  run_all_test = 1

  resource_portal_type = "Product"

  common_sequence_string = """
      CreateOrganisation
      CreateNotVariatedResource
      SetMaxDelayOnResource
      SetMinFlowOnResource
      Tic
      DecreaseOrganisationResourceQuantity
      Tic
      CreateOrderBuilder
      FillOrderBuilder
      Tic
      BuildOrderBuilder
      Tic
      CheckGeneratedDocumentList
      """

  def getTitle(self):
    return "Order Builder"

  def test_01_simpleOrderBuilder(self, quiet=0, run=run_all_test):
    """
    Test simple Order Builder
    """
    if not run: return

    self.wanted_quantity = 1.0
    self.wanted_start_date = DateTime(
      str(self.datetime.earliestTime()
          + self.order_builder_hardcoded_time_diff))

    # We add 4 days to start date to reflect delays
    self.wanted_stop_date = self.wanted_start_date + 4

    sequence_list = SequenceList()
    sequence_list.addSequenceString(self.common_sequence_string)
    sequence_list.play(self)

  @newSimulationExpectedFailure
  def test_01a_simpleOrderBuilderVariatedResource(self, quiet=0, run=run_all_test):
    """
    Test simple Order Builder for Variated Resource
    """
    if not run: return

    sequence_string = """
      CreateOrganisation
      CreateVariatedResource
      SetMaxDelayOnResource
      SetMinFlowOnResource
      Tic
      DecreaseOrganisationResourceQuantityVariated
      Tic
      CreateOrderBuilder
      FillOrderBuilder
      Tic
      BuildOrderBuilder
      Tic
      CheckGeneratedDocumentListVariated
      """

    self.wanted_quantity = 1.0
    self.wanted_start_date = DateTime(
      str(self.datetime.earliestTime() +
          self.order_builder_hardcoded_time_diff))

    self.wanted_stop_date = self.wanted_start_date

    self.decrease_quantity_matrix = {
      'size/Man' : 1.0,
      'size/Woman' : 2.0,
    }

    self.wanted_quantity_matrix = self.decrease_quantity_matrix.copy()

    sequence_list = SequenceList()
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  @newSimulationExpectedFailure
  def test_02_maxDelayResourceOrderBuilder(self, quiet=0, run=run_all_test):
    """
    Test max_delay impact on generated order start date
    """
    if not run: return

    self.max_delay = 14.0

    self.wanted_quantity = 1.0
    self.wanted_start_date = DateTime(
      str(self.datetime.earliestTime()
          - self.max_delay
          + self.order_builder_hardcoded_time_diff))

    self.wanted_stop_date = DateTime(
      str(self.datetime.earliestTime()
          + self.order_builder_hardcoded_time_diff))

    sequence_list = SequenceList()
    sequence_list.addSequenceString(self.common_sequence_string)
    sequence_list.play(self)

  @newSimulationExpectedFailure
  def test_03_minFlowResourceOrderBuilder(self, quiet=0, run=run_all_test):
    """
    Test min_flow impact on generated order line quantity
    """
    if not run: return

    self.wanted_quantity = 1.0
    self.wanted_start_date = DateTime(
      str(self.datetime.earliestTime()
          + self.order_builder_hardcoded_time_diff))

    self.wanted_stop_date = self.wanted_start_date

    sequence_list = SequenceList()
    sequence_list.addSequenceString(self.common_sequence_string)

    # case when min_flow > decreased_quantity
    self.min_flow = 144.0
    self.wanted_quantity = self.min_flow + self.decrease_quantity
    # why to order more than needed?
    # self.wanted_quantity = self.min_flow

    sequence_list.play(self)

    # case when min_flow < decreased_quantity
    self.min_flow = 15.0
    self.decrease_quantity = 20.0

    self.wanted_quantity = self.min_flow + self.decrease_quantity
    # why to order more than needed?
    # self.wanted_quantity = self.decreased_quantity

    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestOrderBuilder))
  return suite

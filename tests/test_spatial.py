from pathlib import Path
import os,sys,unittest
ROOT=Path(__file__).resolve().parents[1]
os.environ['MPLCONFIGDIR']=str(ROOT/'.cache/matplotlib')
(ROOT/'.cache').mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from houseplot import field_scale, rounded_level_scale
from houseplot.spatial import rectilinear_grid,pressure_level,unit_vectors


class SpatialTests(unittest.TestCase):
    def test_negative_db_values_use_observed_level_range(self):
        norm,_=field_scale([np.array([-30.,-10.])],'level')
        self.assertEqual((norm.vmin,norm.vmax),(-30.,-10.))

    def test_grid_preserves_holes_and_rejects_duplicate_coordinates(self):
        x,z,v=rectilinear_grid([0,1,0],[0,0,1],[1,2,3])
        np.testing.assert_equal(v,[[1,2],[3,np.nan]])
        with self.assertRaises(ValueError):rectilinear_grid([0,0],[0,0],[1,2])
        with self.assertRaises(ValueError):rectilinear_grid([0,1,2],[0,1,2],[1,2,3],max_cells=4)

    def test_pressure_level_preserves_undefined_values_without_floor(self):
        result,report=pressure_level([1e-6,1e-5,0,-1,np.nan],reference_pa=1e-6)
        np.testing.assert_allclose(result,[0,20,np.nan,np.nan,np.nan],equal_nan=True)
        self.assertEqual(report['nonpositive'],2)
        self.assertEqual(report['nonfinite'],1)

    def test_normalized_arrows_do_not_create_direction_for_zero_vectors(self):
        u,v,report=unit_vectors([3,0,np.nan],[4,0,1])
        np.testing.assert_allclose(u,[.6,np.nan,np.nan],equal_nan=True)
        np.testing.assert_allclose(v,[.8,np.nan,np.nan],equal_nan=True)
        self.assertEqual(report['undefined'],2)

    def test_rounded_spl_scale_covers_data_with_integer_multiples_of_five(self):
        values=np.array([103.878,223.253])
        norm,cmap,ticks,report=rounded_level_scale([values],quantum=5)
        self.assertEqual((norm.vmin,norm.vmax),(100,225))
        np.testing.assert_equal(ticks,[100,125,150,175,200,225])
        self.assertTrue(report['no_data_clipping'])
        np.testing.assert_equal(values,[103.878,223.253])

    def test_rounding_handles_negative_levels_and_rejects_bad_quantum(self):
        norm,_,ticks,_=rounded_level_scale([np.array([-13.4,26.1])],quantum=5)
        self.assertLessEqual(norm.vmin,-13.4);self.assertGreaterEqual(norm.vmax,26.1)
        np.testing.assert_allclose(ticks/5,np.rint(ticks/5))
        with self.assertRaises(ValueError):rounded_level_scale([np.array([1,2])],quantum=0)

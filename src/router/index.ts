import { createRouter, createWebHistory } from "vue-router";
import HomeView from "../views/HomeView.vue";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: "home",
      component: HomeView,
      children: [
        {
          path: "drone",
          name: "drone",
          component: () => import("../components/Drone.vue"),
        },
        {
          path: "views",
          name: "views",
          children: [
            {
              path: "origin",
              name: "origin",
              component: () => import("../components/Origin.vue"),
            },
            {
              path: "depth",
              name: "depth",
              component: () => import("../components/Depth.vue"),
            },
            {
              path: "pointcloud",
              name: "pointcloud",
              component: () => import("../components/PointCloud.vue"),
            },
            {
              path: "dem",
              name: "dem",
              component: () => import("../components/DEM.vue"),
            },
          ],
        },
        {
          path: "dashboard",
          name: "dashboard",
          component: () => import("../components/Dashboard.vue"),
        },
      ],
    },
    {
      path: "/:pathMatch(.*)*",
      redirect: "/",
    },
  ],
});

export default router;
